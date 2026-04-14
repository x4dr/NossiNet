import json
import queue
import threading
import time
from dataclasses import dataclass

from flask import Blueprint, Response, stream_with_context

from NossiSite.base import log
from NossiSite.base_ext import encode_id, decode_id
from gamepack.WikiPage import WikiPage

views = Blueprint("socks", __name__)


@dataclass
class BroadcastElement:
    name: str
    page: str
    context: str
    type: str
    initial: bool


broadcast_elements: list[BroadcastElement] = []
broadcast = threading.Event()
connected_hubs = set()


@views.route("/sse_updates")
def sse_updates_handler():
    def generate():
        q = queue.Queue()
        connected_hubs.add(q)
        try:
            # Removed the "data: connected" line which was causing JSON parse errors
            yield ": connected\n\n"
            while True:
                update = q.get()
                yield f"data: {json.dumps(update)}\n\n"
        except GeneratorExit:
            pass
        finally:
            if q in connected_hubs:
                connected_hubs.remove(q)

    # Use a response with a proper content-type and cache control
    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@views.route("/sse_test")
def sse_test_handler():
    def generate():
        while True:
            yield f"data: {time.strftime('%H:%M:%S')}\n\n"
            time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "none",
        },
    )


def broadcast_to_hub(payload):
    for q in connected_hubs:
        q.put(payload)


@views.route("/<endpoint>/<name>/<page>/<delta>")
def change_clock(endpoint, name, page, delta):
    log.info(
        f"Incoming clock change: endpoint={endpoint}, name={name}, page={page}, delta={delta}"
    )
    page = decode_id(page)
    name = decode_id(name)
    element_type = "line" if endpoint == "changeline" else "round"
    broadcast_elements.append(BroadcastElement(name, page, "wiki", element_type, False))
    p = WikiPage.load_locate(page, cache=True)
    if p:
        log.info(f"Clock {name} BEFORE change: {p.get_clock(name)}")
        # Re-enabling low priority async save
        p.change_clock(name, int(delta)).save_low_prio("clock")
        # Update cache in memory so subsequent loads hit updated object
        p.cacheupdate()
        log.info(f"Clock {name} AFTER change: {p.get_clock(name)}")
        log.info(f"Clock {name} updated in memory.")

        # Verify and force update cache
        if p.file:
            target_path = p.file.resolve()
            WikiPage.page_cache[target_path] = p

            cached_p = WikiPage.page_cache.get(target_path)
            if not cached_p:
                raise ValueError(
                    f"Verification failed: Clock NOT FOUND in CACHE at key: {target_path}"
                )
            log.info(
                f"Verification: Clock {name} in CACHE is {cached_p.get_clock(name)}"
            )
    else:
        log.warning(f"Could not load page {page} to update clock {name}.")
    broadcast.set()
    return "", 204


def broadcast_clock_update():
    while True:
        broadcast.wait()
        while broadcast_elements:
            element: BroadcastElement = broadcast_elements.pop()
            try:
                if element.context == "wiki":
                    # Enforce absolute path usage
                    if not element.page:
                        raise ValueError("Page path is empty")

                    target_path = (WikiPage.wikipath() / element.page).resolve()
                    # If it's a directory or doesn't end in .md, try adding it to match the cache key
                    if not target_path.suffix == ".md":
                        target_path = target_path.with_suffix(".md")

                    if not target_path.is_absolute():
                        raise ValueError(f"Path {target_path} is not absolute")

                    page = WikiPage.page_cache.get(target_path)
                    log.info(
                        f"Broadcast: Looked up absolute path {target_path}, found in cache? {page is not None}"
                    )

                    if page:
                        clock = page.get_clock(element.name)
                        log.info(
                            f"Broadcast Check: Clock {element.name} on {element.page} state: {clock}"
                        )
                        if not clock:
                            log.warning(
                                f"Could not find clock {element.name} on page {element.page}"
                            )
                            continue

                        pid = f"{encode_id(element.name)}-{encode_id(element.page)}"
                        current_val = int(clock.group("current"))
                        max_val = int(clock.group("maximum"))
                        payload = {
                            "target": pid,
                            "current": current_val,
                            "total": max_val,
                            "type": "clock" if element.type == "round" else "line",
                        }
                        log.info(f"Broadcasting Payload: {payload}")
                        broadcast_to_hub(payload)
                    else:
                        log.warning(
                            f"Broadcast: Page {element.page} (resolved as {target_path}) could not be located in cache."
                        )
                        log.info(
                            f"Page Cache keys: {[str(k) for k in WikiPage.page_cache.keys()]}"
                        )

            except Exception as e:
                log.error(f"Error: {e}")
        broadcast.clear()


def start_threads():
    t = threading.Thread(target=broadcast_clock_update)
    t.daemon = True
    t.start()


def generate_clock(
    active: int, total: int, name="", page="", endpoint="changeclock", initial=False
):
    total = int(total)
    active = int(active)

    ticks = ""
    if total > 1:
        step = 360 / total
        for i in range(total):
            angle = i * step
            ticks += f'<div class="tick" style="transform: rotate({angle}deg);"></div>'

    return f"""
    <div class="clock-container {"cooldown" if not initial else ""}"
         id="{encode_id(name)}-{encode_id(page)}"
         data-active="{active}"
         data-total="{total}"
         data-endpoint="/{endpoint}/{encode_id(name)}/{encode_id(page)}"
         style="--clock-active: {active}; --clock-total: {total};">
         <div class="clock-ticks">{ticks}</div>
    </div>
    """


def generate_line(
    active: int, total: int, name="", page="", endpoint="changeline", initial=False
):
    total = int(total)
    active = int(active)
    boxes = ""
    for i in range(total):
        status = "filled" if i < active else "empty"
        incdec = "-1" if i < active else "1"

        boxes += f"""<div class="gauge-box {status}"
                 data-endpoint="/{endpoint}/{encode_id(name)}/{encode_id(page)}/{incdec}"
                 style="--bouncedelay:{i / total}">
                </div>"""
    return f'<div class="gauge {"" if initial else "cooldown"}" id="{encode_id(name)}-{encode_id(page)}">{boxes}</div>'
