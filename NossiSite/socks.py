import math
import threading
from dataclasses import dataclass

from flask import request, Blueprint, jsonify
from simple_websocket import Server, ConnectionClosed, ConnectionError

from NossiSite.base import log
from NossiSite.base_ext import encode_id, decode_id
from gamepack.PBTACharacter import PBTACharacter
from gamepack.PBTAItem import PBTAItem
from gamepack.WikiCharacterSheet import WikiCharacterSheet
from gamepack.WikiPage import WikiPage

views = Blueprint("socks", __name__)


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


@views.route("/ws_active_element", websocket=True)
def clocks_handler():
    ws = Server.accept(request.environ)
    try:
        name = decode_id(request.args.get("name"))
        page = decode_id(request.args.get("page"))
    except:
        print(str(request))
        raise

    element_type = request.args.get("type") or "round"
    if not name or not page:
        return jsonify({"status": "no valid name"})
    pid = f"{name}-{page}"
    if pid not in connected_clocks:
        connected_clocks[pid] = []
    connected_clocks[pid].append(ws)
    if request.args.get("sheet") == "true":
        context = "sheet"
    else:
        context = "wiki"

    broadcast_elements.append(BroadcastElement(name, page, context, element_type, True))
    broadcast.set()
    try:
        while True:
            log.info(ws.receive())
    except (ConnectionClosed, ConnectionError):
        pass
    return jsonify({"status": "success"})


def send_broadcast(c, element):
    pid = f"{element.name}-{element.page}"
    clients = connected_clocks.get(pid, []).copy()
    for client in clients:
        try:
            client.send(c)
        except (
            ConnectionClosed,
            ConnectionError,
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
                    page = WikiPage.load_locate(element.page)
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
                    char = WikiCharacterSheet.load_locate(element.page).char
                    if not isinstance(char, PBTACharacter):
                        continue
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
                    elif element.name.startswith("item-"):
                        name = element.name[5:]
                        item = char.inventory_get(name)
                        if not item:
                            item = PBTAItem(name, 1, "-", 1, 1)
                        c = generate_line(
                            item.count,
                            item.maximum,
                            element.name,
                            element.page,
                            "change_sheet_line",
                            initial=element.initial,
                        )
                    else:
                        s = char.health_get(element.name)
                        c = generate_line(
                            s[0],
                            s[1],
                            element.name,
                            element.page,
                            "change_sheet_line",
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
                 hx-get="/{endpoint}/{encode_id(name)}/{encode_id(page)}/{incdec}"
                 hx-trigger="click">
            </div>
            <div class="line" style="transform: translate(50%,50%) translateX(-100%) rotate({angle_line}deg);"></div>
        """
    return (
        f'<div class="clock-container '
        f'{"" if initial else "cooldown"}" id={encode_id(name)}-{encode_id(page)}>{slice_html}</div>'
    )


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
                 hx-get="/{endpoint}/{encode_id(name)}/{encode_id(page)}/{incdec}"
                 hx-trigger="click"
                 style="--bouncedelay:{i/total}">
                </div>"""
    return f'<div class="gauge {"" if initial else "cooldown"}" id={encode_id(name)}-{encode_id(page)}>{boxes}</div>'
