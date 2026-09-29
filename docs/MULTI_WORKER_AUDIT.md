# NossiNet multi-worker (`-w N`) safety audit

**Date:** 2026-09-26 (root cause of the wedge identified 2026-09-28 — see item 5)
**Scope:** `~/PycharmProjects/NossiNet` + `~/PycharmProjects/GamePack` (non-test, non-venv).
Note: this checkout is slightly *ahead* of what runs in production.
**Versions:** gunicorn 26.0.0, gevent 26.4.0 (`uv.lock:631-632`, `uv.lock:558-559`).
**Production today:** `gunicorn -b :8000 --worker-class gevent -w 1 NossiNet:app`

## Why this audit exists

The single gunicorn worker occasionally wedges — it stops accepting TCP connections
entirely, so nginx logs `upstream timed out (110: Connection timed out) while connecting
to upstream` even for trivial paths like `/`. With `-w 1` there is no fallback process,
so the whole site goes down while the host itself stays responsive (SSH, nginx, and the
box are all fine).

The obvious mitigation is more workers plus a gunicorn `--timeout`. But the site owner
suspects some state lives in process memory and is shared across requests, which would
break under multiple workers. This document is the inventory of that state.

> **Addendum (2026-09-28).** The wedge is now **root-caused and fixed**, and it was
> *not* cured by more workers — it was caused by the SSE hub leaking gunicorn pool
> slots, so `-w 4` would have made the pool 4× larger while the leak drained it 4×
> faster. See item 5 for the measurement, item 6 for the retracted "more capacity"
> argument, and `tests/test_sse_disconnect.py` for the regression test. The state
> inventory below still holds and the verdict is still **UNSAFE as-is** for `-w N`;
> that question is simply not the one that was breaking the site.

## Verdict

**UNSAFE as-is.** The single biggest blocker is the in-process SSE broadcast hub:
`NossiSite/socks.py:33-35` keeps `broadcast_elements`, a `threading.Event`, and a
`connected_hubs` set **in module memory**, and `broadcast_to_hub` (`socks.py:112-115`)
only pushes to queues owned by its *own* process. A browser `EventSource`
(`NossiSite/static/js/sse.js:77`) holds one long-lived TCP connection to `/sse_updates`
for the life of the page, so that connection is pinned to one worker forever. At `-w 4`,
a chat message, dice roll, or clock tick published on worker B is **silently dropped**
for every subscriber pinned to workers A/C/D — not delayed, dropped, because the payload
never leaves the publishing process. Three separate features (chat, dice rolls, clocks)
publish through this one hub.

Two secondary blockers: a git-commit coordination scheme (`commit_tmp` + per-process
`saveat`) that loses commits when processes collide on `~/wiki/.git/index.lock`, and a
boot-time `BEGIN TRANSACTION` clock sync that runs in every worker with no WAL and no
`busy_timeout`, which can hard-fail the worker at import.

## Blocking issues

| Item | File:line | Why it breaks with >1 worker | Severity |
|---|---|---|---|
| SSE hub fan-out is process-local | `NossiSite/socks.py:33-35` (`broadcast_elements`, `broadcast = threading.Event()`, `connected_hubs = set()`), `socks.py:63-77` (per-connection `queue.Queue` added at 65), `socks.py:112-115` (`for q in connected_hubs: q.put(...)`) | Publishers: clocks `socks.py:202`, chat `chat.py:109` (import at `chat.py:19`), dice rolls `sheets.py:726` (import at `sheets.py:38`). A publish on worker B iterates only B's `connected_hubs`. Subscribers pinned to A/C/D never see it. No error, no retry — total, silent message loss for ~3/4 of clients. | **CRITICAL** |
| Clock broadcast drops if page not in *this* worker's cache | `socks.py:181` (`WikiPage.page_cache.get(target_path)`), `socks.py:209-214` (warn + `continue`) | Compounds the row above. `page_cache` is per-process and starts **empty** in each worker; nothing warms it at boot (`clock_sync.py:31` only calls `wikindex()`, which lists paths without loading). Even in the lucky case where publisher and subscriber share a worker, the page must be in that worker's cache or the broadcast is dropped with only a `log.warning`. | HIGH |
| Wiki checkbox state: process-local, keyed by nothing | `wiki.py:272-286` (`_checkbox_state: dict[str, bool] = {}`; `checkbox_toggle` read-modify-write at 279-280) | Keyed only by the wiki path — no user, no session. Already wrong at `-w 1` (one user's toggle is everyone's). With N workers it splits into N independent dicts, and the HTMX round trip (`hx-get="/checkbox/{key}"` at 283, then the browser re-GETs the same URL) can land on different workers, so the checkbox **flips back**. Also grows unboundedly per process. | HIGH |
| Git commit coordination is process-local + a shared un-locked file | `WikiPage.py:599` (`saveat = None`), `:615` (`global saveat`), `:625-626` (append to CWD-relative `commit_tmp`), `:631-636` (spawn per-process push greenlet), `:581-586` (read + `commitfile.unlink()`); reached from `save()` `:270`, `save_overwrite()` `:311`, and the savequeue greenlet `:655` | (a) `Path("commit_tmp")` is relative to CWD, shared by all workers. append→append→read→unlink has no lock → messages lost; the observed `NossiNet/commit_tmp` (1332 bytes, 30 unconsumed `edited by ` lines) shows it already fails to drain. (b) Each worker's own `saveat` calls `repo.index.commit()` on the same `~/wiki/.git`. GitPython `IndexFile` is per-process, not shared; concurrent commits collide on `index.lock` → the loser raises and its staged change is left staged. | HIGH |
| Shared SQLite file with no WAL and no `busy_timeout` | `Data/__init__.py:38` (`sqlite3.connect(dbpath, check_same_thread=False)` — no `timeout=`, no `PRAGMA`); zero hits for `journal_mode\|WAL\|busy_timeout\|PRAGMA` in either repo | Default rollback-journal + `busy_timeout=0` means a second writer gets `SQLITE_BUSY` **immediately**, no waiting. At `-w 1` there was only ever one connection. N workers = N connections = real contention on every write path (`socks.py:144-148`, `Chatrooms.py:93-98`, `User.py` writes). | HIGH |
| Deferred-transaction clock sync runs at import in every worker | `NossiNet.py:22` → `socks.py:221-226` (`start_threads`) → `clock_sync.py:15`, `:48` (`BEGIN TRANSACTION` — *deferred*), `:51-53` (writes only to a TEMP table), `:55-62` (first touch of the main DB), `:88-90` (`rollback()` then `raise`) | A deferred transaction that must **upgrade** to a write lock while another process holds one cannot wait — it fails. With 4 workers booting together this is likely. Because it re-raises at module import, the worker dies, gunicorn respawns it, and it happens again → boot loop. | HIGH |
| `sync_clocks_with_db` silently resets live clock values on every worker boot | `clock_sync.py:55-62` (overwrite `clocks` from `.md`), `:74-82` (delete rows not in `.md`); vs. `socks.py:144-148` which writes **only** the DB and never the `.md` | At `-w 1` this ran once per full restart. With `-w 4` it runs on *every individual worker respawn*, at unpredictable times, discarding clock increments players have made. | MEDIUM-HIGH |
| Startup schema race on a fresh DB | `Data/__init__.py:35-37` (`if not Path(dbpath).exists(): touch(); init_db()`), `:18-23` (`init_db` → `executescript(getschema())`) | N workers starting together on an empty file all observe "not exists" and all run `executescript` concurrently. First-boot only. | LOW |

## Safe to duplicate per process

| Item | File:line | Why it's fine per-process |
|---|---|---|
| `Data.g` connection cache | `Data/__init__.py:14`, `:26-40` | The singleton is per-process, so N workers = N connections to the same file. The `check_same_thread=False` at `:38` is a **within-process** greenlet-sharing hack (needed because the `broadcast_clock_update` greenlet started at `socks.py:224` also calls `connect_db` via `get_clock_from_db` at `socks.py:49`), *not* an inter-process hand-off. `close_db` (`:43-48`) is only used by tests (`tests/NossiTestCase.py:34`) — connections are never closed in production, but that is pre-existing. |
| `WikiPage.page_cache` | `WikiPage.py:36`; validity check `:181-183` | Pure shadow cache, and it is **mtime-validated on read**: reuse only if `result.file.stat().st_mtime == result.last_modified`. A write by another process changes mtime → cache miss → re-read from disk. Authoritative state is the `.md` file plus git. |
| `WikiPage.wikicache` (tag/link index) | `WikiPage.py:37`; rebuild `:406-431`; glob source `:363-379`; self-clear `:413-415` | Derived index, fully rebuildable from the filesystem by `updatewikicache()`. Clears itself when >60s stale. |
| `WikiPage._wikipath` | `WikiPage.py:38`; set at import `wiki.py:38` | Set once from a constant (`Path.home() / "wiki"`) at import time, identical in every process. `set_wikipath` raises if called twice (`WikiPage.py:110-111`), but it is only ever called once per process. |
| `WikiPage.wikistamp`, `wiki.py:39 wikistamp = [0.0]` | `WikiPage.py:39`; `wiki.py:39` | Timestamps only. |
| `ItemBase.item_cache` | `ItemBase.py:120`; rebuild `WikiPage.py:434-460` | Derived from wiki pages; rebuilt by `cache_items()` from disk. **Footnote:** `cache_items()` currently has **zero** call sites, and the guard at `WikiPage.py:67` tests `is None` while the default is `{}` — so this cache is empty in every process today. See "Needs care" #4. |
| Dice-cache connection | `gamepack/__init__.py:10`, `:33-48` | Per-process singleton to `data/dicecache.sqlite`, a pure memo of dice results. Same missing-WAL exposure as the main DB, but writes are tiny. |
| `@lru_cache` on the calculator | `gamepack/Calc.py:160` (maxsize=1024) | Pure function of its arguments; no I/O, no shared state. |
| `@lru_cache` on discord-id resolution | `NossiPack/Chatrooms.py:26-34` (maxsize=50) | Memo of a single-row DB read. Per-process staleness only, and the *same* staleness already exists at `-w 1`. |
| Import-time registries | `NossiTag.registry` `markdown/base.py:31` (filled `:42-61`); `_renderers` `renderers/__init__.py:13,23` (+ import `:43`); `stage_handlers` `sheets.py:281,295` (+ decorators `:316,335`) | Populated deterministically at import; identical content in every process. |
| Shared `NossiMarkdownProcessor` instances | `wiki.py:40`, `sheets.py:148`, `renderers/characterrenderer.py:19`; class `markdown/__init__.py:21-138` | Each instance holds only `self.tags` (`markdown/__init__.py:34`), and a fresh `WikiEnvironment` is built per `render()` call (`:93`). Effectively immutable during rendering → safe to share across concurrent requests. |
| `chat.data` bridge config | `chat.py:26-31`; loaded once by `init()` at `chat.py:227` | Read-only snapshot of the DB `configs` table taken at boot. No writes → no split brain, only propagation lag (see "Needs care" #2). |
| Flask session / login | `base.py:17-26` (`SECRET_KEY` from `~/key`), `:26-32` (`app.config.from_object`); **no** `session_interface` / `flask_session` anywhere (verified: zero hits) | Default **signed-cookie** session. All state travels in the cookie, so **no session affinity is required** — any worker can serve any session. `sheets.py:275-277,309-313` (`session["character_gen"]`) and `extra.py:78` (`session["lock"]`) are cookie-resident. |
| `MechaEncounterManager` | `sheets.py:110,891,936`; class `mecha_history.py:11-26` | Instantiated fresh per request; state lives in `~/wiki/encounters/*.json` (`mecha_history.py:21-23`). Filesystem is the substrate. |
| Blueprints | `views.py:38`, `socks.py:19`, `chat.py:21`, `extra.py:31`, `sheets.py:149` | Per-process registration at import; idempotent. |
| `statisticsroller.exp_t` | `statisticsroller.py:288` | **Never imported** (verified: zero references anywhere in the repo) → not part of the running app. |
| `fengraph` precomputed tables | `gamepack/fengraph.py:325-326` | Immutable numeric constants computed at import. |
| `NossiTag` render-time stacks | `infolet.py:10,45,48`; `section_tooltip.py:49-50,67,70` | Module-level, but push/pop is balanced within a single `post_process` call and there is no I/O or yield point inside, so gevent will not switch greenlets mid-function. Per-process duplication is harmless. The `iq-N` / `tip-N` id counters collide *across* workers, but each document carries both the trigger and its `tip-content` div, so uniqueness is only needed within a response. |
| `nossilog.log` append handler | `base.py:34` | `mode="a"` from N processes — interleaved lines, no corruption of the app's state. |

## Needs care / needs a decision

1. **`restart_id` cache-buster becomes per-worker.** Set at `base.py:39`, and
   **reassigned at request time** at `views.py:116` inside `save_theme`. It is a Jinja
   global used as `?v=` on ~40 asset URLs (e.g. `templates/base/layout.html:15-17`,
   `templates/wiki/wikipage.html:48-52`). Regenerating it bumps only the worker that
   served `/savetheme`; the other N-1 keep emitting the old value, so theme/asset changes
   stop reaching most users. *Decision:* make it a constant, or persist it (e.g. into the
   `configs` table) and read per request.

2. **`chat.data` bridge config propagates only on restart.** `chat.py:26-31` + `init()` at
   `chat.py:227`. A Discord webhook/`channelid` change lands in the DB but each worker
   needs its own restart. Tolerable today only because `webhook.py:57` already does a
   full `systemctl restart` on pushes. *Decision:* accept, or read `configs` per broadcast.

3. **`wikicache` staleness is now unsynchronised across workers.** `WikiPage.py:37,406-431`
   plus the `after_app_request` trigger at `wiki.py:60-69` (fires when `wikicache` is empty
   or `WikiPage.wikistamp` is >15min old, spawning a greenlet at `:68`). Each worker runs
   its own 60s/15min timers, so `gettags()`-driven tag search (`wiki.py:98-119`) and
   `page_cache` warming drift independently. Not corruption, but listings will differ by
   worker. *Decision:* accept, or move the 60s window into a shared mtime/marker.

4. **`Item.item_cache` is dead code today — don't "fix" it blindly.** `WikiPage.py:67`
   guards on `if Item.item_cache is None` but `ItemBase.py:120` defaults to `{}`, and
   `cache_items()` has zero call sites. So the item cache is empty in every process, which
   means infolet tooltips (`infolet.py:70` `Item.item_cache.get(name)`) render nothing. If
   someone adds a `cache_items()` call, the per-worker staleness question comes back (the
   cache is derived from wiki files, so it would need the same invalidation discipline as
   `page_cache`).

5. **The wedge was the SSE hub leaking gunicorn pool slots. [SUPERSEDED — now MEASURED]**

   > **This item previously read:** *"The wedge is probably not the SSE hub — likely a
   > blocking C call. [INFERRED]"* naming two unbounded queries. **That inference was
   > wrong, and is retained below only as a record of the mistake.** The real cause is
   > fixed in `NossiSite/socks.py`; see `tests/test_sse_disconnect.py`.
   >
   > The generator blocked in an **untimed** `q.get()`. It never checked whether the
   > client was still there, so on disconnect it never raised, never ran its
   > `finally`, and never returned its pool slot. `StreamServer` only calls `accept()`
   > when `pool.spawn()` has a free slot (`ggevent.py:78`, `Pool(worker_connections)`,
   > default 1000), so once ~1000 clients had ever disconnected, the worker stopped
   > accepting entirely: `LISTEN 2049 2048` on `:8000` (accept queue pinned full), SYNs
   > dropped, nginx logging `upstream timed out (110) *while connecting to upstream*`.
   >
   > **Measured, not inferred** (production, 2026-09-28): the worker held 1003 socket
   > fds = 1000 client sockets + 1 LISTEN + 2 inherited stdio, matching the pool size
   > exactly; ~1700 sockets in `CLOSE-WAIT`; `py-spy` showing the single thread
   > **idle** in `gevent/hub.py:647` with no greenlet running (a blocked SQLite call
   > would instead show an active thread *inside* the query); and the app's own log
   > going silent at `2026-09-26 04:29:58` with no traceback. nginx reporting a
   > *connect* timeout rather than a *read* timeout is what rules the query theory out
   > — nothing ever reached a query.
   >
   > The original reasoning failed by asking "what could block the hub?" and stopping
   > at the first candidate, instead of asking "why did the hub have nothing to do?"
   > It was idle, not blocked. The two queries named in the old text are still worth
   > bounding, but they did not cause this outage.

6. **`--timeout` will *not* kill your SSE connections (verified — worth stating explicitly).**
   `--timeout` is a *heartbeat* watchdog, not a request deadline: `base_async.py` applies
   `timeout_ctx()` only around reading the next keepalive request, not around iterating the
   response body, and `ggevent.py:run()` calls `notify()` from its own greenlet. An open
   `/sse_updates` stream does not trip it. Note also that `Pool(self.worker_connections)` is
   **per worker** (default 1000, `config.py:764-776`) and `ggevent.py:run()` sets
   `server.max_accept = 1` when `workers > 1`.

   > **Correction.** The original text concluded from the per-worker pool that
   > *"more workers genuinely multiplies total SSE capacity — that is the real upside
   > of the change."* The arithmetic is right and the conclusion is wrong. That pool is
   > the thing that was leaking (see item 5): a bigger pool is a bigger buffer in front
   > of the same unbounded leak, so `-w 4` would have quadrupled the pool to 4000 slots
   > **and** quadrupled the rate at which slots are lost — buying time, not a fix. The
   > leak is fixed at the source in `socks.py`; `-w` is not part of the remedy.

7. **Recommended minimal path to `-w 4`, in order:**
   (a) move the SSE hub to Redis pub/sub or a `gunicorn`-compatible broker — this is
   mandatory, not optional;
   (b) add `PRAGMA journal_mode=WAL` + `busy_timeout` on connect at `Data/__init__.py:38`
   and guard `clock_sync` so a `SQLITE_BUSY` at import cannot kill the worker
   (`clock_sync.py:88-90`);
   (c) serialise the git commit path behind a file lock or an out-of-process committer, and
   make `commit_tmp` unique per process;
   (d) make `_checkbox_state` (`wiki.py:272`) per-session or move it to the DB.

## Evidence appendix

**Commands run (read-only).** `find`/`wc -l` over both repos; targeted `grep -rn` for
`connect_db|close_db|sqlite3|check_same_thread`, `lru_cache|functools|@cache|memoize`,
`threading\.|Lock()|Event()|Queue(|multiprocessing|subprocess`,
`set_wikipath|wikipath`, `journal_mode|WAL|busy_timeout|PRAGMA|isolation_level`,
`session_interface|flask_session`, `start_savequeue|savequeue|start_threads`,
`broadcast_to_hub`, `chara_objects|_checkbox_state|restart_id|stage_handlers|_renderers`,
`cache_items`, `sse-connect|sse_updates`, `EventSource`; plus an AST walk of every
non-test `.py` in both repos for module-level and class-level mutable bindings. The AST
walk is what produced the exhaustive list in the tables — it is why the set of module-level
mutable globals can be considered complete rather than "the ones that were noticed".

**Files read in full or in substantial part.** `NossiNet.py`, `Data/__init__.py`,
`Nossigevent.py`, `NossiSite/socks.py` (302 lines), `NossiSite/base.py`,
`NossiSite/helpers.py`, `NossiSite/chat.py` (227), `NossiSite/clock_sync.py` (90),
`NossiSite/__init__.py`, `NossiSite/webhook.py`, `NossiSite/wiki.py` (1-120, 250-369),
`NossiSite/sheets.py` (270-339, 700-744), `NossiSite/views.py` (1-200, 340-459),
`NossiSite/extra.py` (1-80), `NossiSite/renderers/__init__.py`,
`NossiSite/mecha_history.py` (via grep), `NossiPack/Chatrooms.py` (205),
`NossiPack/User.py` (1-120, Userlist/Config via grep), `NossiPack/markdown/__init__.py`
(138), `NossiPack/markdown/base.py` (111), `NossiPack/markdown/tags/infolet.py` (82),
`NossiPack/markdown/tags/section_tooltip.py` (1-80), `GamePack/gamepack/WikiPage.py` (662),
`GamePack/gamepack/__init__.py` (48), `GamePack/gamepack/ItemBase.py` (110-130).

**Files read to verify third-party behaviour.** `.venv/.../gunicorn/workers/ggevent.py`
(full), `base_async.py` (full), `base.py` (notify/heartbeat lines), `arbiter.py:576-595`
(`murder_workers`), `config.py:764-830` (`worker_connections` default 1000, `timeout`
default 30, `max_requests` default 0). Versions confirmed from `uv.lock:631-632`
(gunicorn 26.0.0) and `uv.lock:558-559` (gevent 26.4.0).

**On-disk checks (read-only).** `~/wiki/.git` exists (wiki is a real git repo);
`~/wiki/.git/index.lock` absent at the time of checking; `NossiNet/commit_tmp` exists,
1332 bytes, 30 repeated `/home/maric/wiki/demo.md edited by ` lines — the observable
residue of `WikiPage.py:625-626` appending and `:581-586` never successfully unlinking.
`NossiSite/static/js/sse.js:77` is `new EventSource(url, {withCredentials: true})`, and
`templates/base/chat.html:10` is `hx-ext="sse" sse-connect="/sse_updates"` — one
long-lived connection per page, which is what pins a subscriber to a single worker.

**On the wedge (added 2026-09-28).** Diagnosed from a live, wedged production worker
using only reads: `ss -ltnp` (accept queue `Recv-Q 2049` against a 2048 backlog),
`/proc/<pid>/fd` (1003 socket fds vs. a 1000-slot pool), `ss -tanp` state breakdown
(~1700 `CLOSE-WAIT`), `/proc/<pid>/stack` (single thread in `do_epoll_wait`), and the
pre-existing `nossinet-watchdog.service` captures in
`/var/log/nossinet-watchdog/dumps/` (py-spy showing the thread **idle** in
`gevent/hub.py:647`, 7095 consecutive failed probes). `py-spy` is not installed in the
app venv but is present at the path the watchdog uses. No service was restarted or
reconfigured during diagnosis.

**VERIFIED vs INFERRED.** Everything in the two tables is VERIFIED by reading the cited
code. Four items are reasoning rather than measurement: (i) the claim that the deferred
transaction at `clock_sync.py:48` *will* fail under concurrent boot is derived from
SQLite's documented deferred-upgrade semantics, not from an observed failure; (ii)
`statisticsroller.py` not being imported is a grep result, so it is absent from the import
graph as of this checkout; (iii) the two-query wedge theory formerly in item 5 was
inference and has since been **measured and refuted** — see item 5; (iv) the two queries
themselves are still worth bounding, but that is a separate, unverified concern.

**One thing deliberately not chased.** `WikiPage.py:66` puts `save_msg_queue` on the
*instance*, and the savequeue greenlet (`WikiPage.py:639-655`) walks
`WikiPage.page_cache.values()` — the same process's cache. So a low-priority save enqueued
by worker B *is* flushed by worker B's own greenlet, and the N greenlets do not
double-save the same edit. This initially looked like a duplication bug; it is not one.
It is noted because it resembles a split-brain bug on a first read.
