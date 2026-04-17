import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from flask import Blueprint, Response, stream_with_context


from Data import connect_db
from NossiSite.base import log
from NossiSite.base_ext import encode_id, decode_id
from gamepack.WikiPage import WikiPage
from scripts.sync_clocks import sync_clocks_with_db

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


def get_clock_from_db(name, page_id, context):
    db = connect_db(f"socks.{context}")
    return db.execute(
        "SELECT current_val, total_val FROM clocks WHERE clock_name = ? AND page_id = ?",
        (name, page_id),
    ).fetchone()


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
            log.info("SSE Hub: Client disconnected")
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
    page_id = decode_id(page)
    name = decode_id(name)
    delta = int(delta)

    # Path resolution:
    # 1. Start with the decoded page path (which is currently just 'clocks')
    # 2. Try to resolve it to the relative path stored in the DB (like 'clocks.md')
    target_page_id = page_id
    if not target_page_id.endswith(".md"):
        # We need to find the correct relative file path
        # Try finding the file in the wiki
        possible_files = list(WikiPage.wikipath().glob(f"**/{page_id}.md"))
        if possible_files:
            target_page_id = str(possible_files[0].relative_to(WikiPage.wikipath()))
        else:
            target_page_id += ".md"

    # Update DB
    db = connect_db("socks.change_clock")
    cursor = db.cursor()
    cursor.execute(
        "UPDATE clocks SET current_val = MIN(total_val, MAX(0, current_val + ?)) WHERE clock_name = ? AND page_id = ?",
        (delta, name, target_page_id),
    )
    db.commit()

    element_type = "line" if endpoint == "changeline" else "round"
    # broadcast_elements.append needs to pass the same page id we used in the update
    # which is target_page_id
    broadcast_elements.append(
        BroadcastElement(name, target_page_id, "wiki", element_type, False)
    )
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
                    if page:
                        # Use relative path for clock lookup
                        try:
                            rel_page = str(
                                Path(element.page).relative_to(WikiPage.wikipath())
                            )
                        except ValueError:
                            rel_page = element.page
                        row = get_clock_from_db(element.name, rel_page, "broadcast")

                        if row:
                            current_val, max_val = row
                            pid = f"{encode_id(element.name)}-{encode_id(element.page)}"
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
                                f"Could not find clock {element.name} in DB on page {rel_page}"
                            )
                            continue

                    else:
                        log.warning(
                            f"Broadcast: Page {element.page} (resolved as {target_path}) could not be located in cache."
                        )

            except Exception as e:
                log.error(f"Error: {e}")
        broadcast.clear()


def start_threads():
    sync_clocks_with_db()
    t = threading.Thread(target=broadcast_clock_update)
    t.daemon = True
    t.start()


def generate_clock(
    active: int, total: int, name="", page="", endpoint="changeclock", initial=False
):
    total = int(total)
    # page might be relative, ensure consistent lookup
    # strip wiki base if present
    rel_page = (
        str(Path(page).relative_to(WikiPage.wikipath()))
        if Path(page).is_absolute()
        else page
    )
    if not rel_page.endswith(".md"):
        rel_page += ".md"

    # Try to fetch current value from DB
    row = get_clock_from_db(name, rel_page, "generate_clock")
    if row:
        active = row[0]

    ticks = ""
    if total > 1:
        step = 360 / total
        for i in range(total):
            angle = i * step
            ticks += f'<div class="tick" style="transform: rotate({angle}deg);"></div>'

    return f"""
    <div class="clock-container {"cooldown" if not initial else ""}"
         id="{encode_id(name)}-{encode_id(rel_page)}"
         data-active="{active}"
         data-total="{total}"
         data-endpoint="/{endpoint}/{encode_id(name)}/{encode_id(rel_page)}"
         style="--clock-active: {active}; --clock-total: {total};">
         <div class="clock-ticks">{ticks}</div>
    </div>
    """


def generate_line(
    active: int, total: int, name="", page="", endpoint="changeline", initial=False
):
    total = int(total)
    # page might be relative, ensure consistent lookup
    rel_page = (
        str(Path(page).relative_to(WikiPage.wikipath()))
        if Path(page).is_absolute()
        else page
    )
    if not rel_page.endswith(".md"):
        rel_page += ".md"

    # Try to fetch current value from DB
    row = get_clock_from_db(name, rel_page, "generate_line")
    if row:
        active = row[0]

    boxes = ""
    for i in range(total):
        status = "filled" if i < active else "empty"
        incdec = "-1" if i < active else "1"

        boxes += f"""<div class="gauge-box {status}"
                 data-endpoint="/{endpoint}/{encode_id(name)}/{encode_id(rel_page)}/{incdec}"
                 style="--bouncedelay:{i / total}">
                </div>"""
    return f'<div class="gauge {"" if initial else "cooldown"}" id="{encode_id(name)}-{encode_id(rel_page)}">{boxes}</div>'
