import math
import threading
from dataclasses import dataclass

import simple_websocket
from flask import request
from flask_sock import Sock

from NossiSite.base import log
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage

sock = Sock()


@dataclass
class BroadcastElement:
    name: str
    page: str
    context: str
    type: str
    initial: bool


broadcast_elements: [BroadcastElement] = []
broadcast = threading.Event()
connected_clocks = {}


@sock.route("/active_element")
def clocks_handler(ws):
    name = request.args.get("name")
    page = request.args.get("page")
    element_type = request.args.get("type") or "round"
    pid = f"{name}-{page}"
    if not name:
        return
    if name not in connected_clocks:
        connected_clocks[pid] = []
    connected_clocks[pid].append(ws)
    if request.args.get("sheet") == "true":
        context = "sheet"
    else:
        context = "wiki"

    broadcast_elements.append(BroadcastElement(name, page, context, element_type, True))
    broadcast.set()
    print(f"adding {pid} for clocks")
    while True:
        log.info(ws.receive())


def send_broadcast(c, element):
    pid = f"{element.name}-{element.page}"
    clients = connected_clocks.get(pid, []).copy()
    for client in clients:
        try:
            client.send(c)
        except (
            simple_websocket.ConnectionClosed,
            simple_websocket.ConnectionError,
        ):
            connected_clocks[pid].remove(client)
            if not connected_clocks[pid]:
                del connected_clocks[pid]


def broadcast_clock_update():
    while True:
        broadcast.wait()
        while broadcast_elements:
            element: BroadcastElement = broadcast_elements.pop()
            try:
                if element.context == "wiki":
                    page = WikiPage.load_str(element.page)
                    clock = page.get_clock(element.name)
                    if not clock:
                        continue
                    if element.type == "round":
                        c = generate_clock(
                            clock.group("current"),
                            clock.group("maximum"),
                            element.name,
                            element.page,
                            initial=element.initial,
                        )
                    else:
                        c = generate_line(
                            clock.group("current"),
                            clock.group("maximum"),
                            element.name,
                            element.page,
                            initial=element.initial,
                        )
                else:  # if element.context == "sheet":
                    char = WikiCharacterSheet.load_str(element.page).char
                    if element.name == "healing":
                        healing = char.health_get(element.name)
                        c = generate_clock(
                            healing[0],
                            healing[1],
                            element.name,
                            element.page,
                            "change_sheet_clock",
                            initial=element.initial,
                        )
                    else:
                        s = char.health_get(element.name)
                        c = generate_line(
                            s[0],
                            s[1],
                            element.name,
                            element.page,
                            "change_sheet_clock",
                            initial=element.initial,
                        )
                send_broadcast(c, element)
            except Exception as e:  # don't stop for any reason
                print(e)
                raise
        broadcast.clear()


def start_threads():
    t = threading.Thread(target=broadcast_clock_update)
    t.daemon = True
    t.start()


def generate_clock(
    active: int, total: int, name="", page="", endpoint="changeclock", initial=False
):

    def generate_clip_path(segments):
        fraction = 1 / segments
        radius = 55  # Percentage radius
        center_x, center_y = 50, 50  # Center of the circle in percentage
        helper = 8
        angle = 360 * fraction / helper
        angle_rad = math.radians(angle)

        points = [f"{center_x}% {center_y}%"]
        for i in range(helper + 1):
            theta = angle_rad * i
            x = center_x + radius * math.cos(theta)
            y = center_y + radius * math.sin(theta)
            points.append(f"{x}% {y}%")
        points.append(f"{center_x}% {center_y}%")
        return f"polygon({', '.join(points)})"

    slice_html = ""
    total = int(total)
    active = int(active)
    for e in range(total):
        color = " active" if e < active else ""
        clip_path = generate_clip_path(total)
        angle_shape = (360 / total) * e - 90
        angle_line = angle_shape - 90
        incdec = "-1" if e < active else "1"

        slice_html += f"""
            <div class="segment{color}"
                 style="clip-path: {clip_path}; transform: rotate({angle_shape}deg);"
                 hx-get="/{endpoint}/{name}/{page}/{incdec}"
                 hx-trigger="click">
            </div>
            <div class="line" style="transform: translate(50%,50%) translateX(-100%) rotate({angle_line}deg);"></div>
        """
    return f'<div class="clock-container {"" if initial else "cooldown"}" id={name}-{page}>{slice_html}</div>'


def generate_line(
    active: int, total: int, name="", page="", endpoint="changeline", initial=False
):

    total = int(total)
    active = int(active)
    boxes = ""
    for i in range(total):
        status = "filled" if i < active else "empty"
        incdec = "-1" if i < active else "1"

        boxes += f"""<div class="gauge-box {status}""
                 hx-get="/{endpoint}/{name}/{page}/{incdec}"
                 hx-trigger="click"
                 style="--bouncedelay:{i/total}">
                </div>"""
    return f'<div class="gauge {"" if initial else "cooldown"}" id={name}-{page}>{boxes}</div>'
