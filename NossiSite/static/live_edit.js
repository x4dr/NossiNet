window.addEventListener("load", () => {
    const csrf_token = document.querySelector('meta[name="csrf-token"]').content;
    const accentColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--accent-color').trim();
    let lock_edit_content = false;
    window.get_edit_content =
        (con, ref) => {

            return async () => {
                if (lock_edit_content) return;
                lock_edit_content = true
                const path = (ref.dataset.path ?? "").split("|");
                const percentage = ref.dataset.percentage || "";
                let req = {"context": con, "path": path, "percentage": percentage}
                req.type = ref.dataset["type"] || "text";
                const response = await fetch("/live_edit", {
                    method: 'POST',
                    body: JSON.stringify(req),
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrf_token
                    }
                });
                let reply;
                try {
                    reply = await response.json(); //extract JSON from the http response
                } catch (e) {
                    reply = {"data": ""}
                    alert("Internal Server Error!")
                }
                lock_edit_content = false;
                if (reply["data"].length < 1) {
                    ref.className = ref.className.replace("editable", "failed")
                    ref.onclick = () => {
                    };
                } else {
                    if (reply["type"] === "table") {
                        table_row_overlay_edit(reply)
                    } else {
                        overlay_edit(reply)
                    }
                }
            }
        };


    function overlay_edit(reply) {
        const editfield = document.getElementById("editfield");
        const overlay = document.getElementById("overlay");
        const textdiv = editfield.querySelector("textarea");
        const olddata = editfield.querySelector("[name='original']");
        const closebutton = editfield.querySelector("[name='closebutton']");
        editfield.className = "editfield"
        editfield.classList.add("activeedit");
        textdiv.value = reply["data"];
        olddata.value = reply["data"];
        textdiv.focus();
        textdiv.click();
        overlay.style.opacity = "1";
        overlay.style.zIndex = "1";
        closebutton.onclick = () => {
            document.body.style.overflow = "auto"
            editfield.className = "editfield"
            textdiv.value = ""
            olddata.value = ""
            overlay.style.opacity = "0";
            overlay.style.zIndex = "-1";
        }
    }

    function table_row_overlay_edit(reply) {
        const editfield = document.getElementById("table_editor");
        const overlay = document.getElementById("overlay");
        const table = editfield.querySelector("table");
        const addbutton = editfield.querySelector("[name='addtable_entry']");
        const closebutton = editfield.querySelector("[name='closebutton']");
        const headers = reply["data"]["headers"];
        const rows = reply["data"]["rows"];
        editfield.querySelector("[name='styles']").value = reply["data"]["styles"];
        editfield.querySelector("[name='path']").value = JSON.stringify(reply["path"]);

        let header_row = table.querySelector("thead tr");
        header_row.innerHTML = "";
        for (let i = 0; i < headers.length; i++) {
            let cell = document.createElement('th');
            let input = document.createElement('input');
            input.value = headers[i];
            input.className = "bright"
            input.style.padding = "5px";
            input.style.alignContent = "center";
            input.style.color = getComputedStyle(document.documentElement).getPropertyValue('--text-color');
            input.name = "header_" + i;
            cell.appendChild(input);
            header_row.appendChild(cell);
        }
        let tbody = table.querySelector("tbody");
        tbody.innerHTML = "";
        for (let i = 0; i < rows.length; i++) {
            let row = document.createElement('tr');
            for (let prop in rows[i]) {
                let cell = document.createElement('td');
                let input = document.createElement('input');
                input.value = rows[i][prop];
                input.className = "dark"
                input.name = "table_" + i + "_" + prop;
                cell.appendChild(input);
                row.appendChild(cell);
            }
            tbody.appendChild(row);
        }
        editfield.classList.add("activeedit");
        overlay.style.opacity = "1";
        overlay.style.zIndex = "1";
        closebutton.onclick = () => {
            document.body.style.overflow = "auto"
            editfield.className = "editfield_table"
            overlay.style.zIndex = "-1";
            overlay.style.opacity = "0";
        }
        addbutton.onclick = () => {
            let row = document.createElement('tr');
            for (let i = 0; i < headers.length; i++) {
                let cell = document.createElement('td');
                let input = document.createElement('input');
                input.value = "";
                input.className = "dark"
                input.name = "table_" + rows.length + "_" + i;
                cell.appendChild(input);
                row.appendChild(cell);
            }
            rows.push(row);
            tbody.appendChild(row);
        }
    }


    const anchors = document.getElementsByClassName('editable');
    const context_elem = document.getElementById('context_element');
    if (context_elem != null) {
        const context = context_elem.innerHTML;
        context_elem.remove();
        for (let i = 0; i < anchors.length; i++) {
            let anchor = anchors[i];
            anchor.ondblclick = get_edit_content(context, anchor)
        }
    }
    let picked = [];
    const svg = document.getElementById("conn-svg");
    const NS = "http://www.w3.org/2000/svg";

    let mouseX = 0, mouseY = 0;
    document.addEventListener("mousemove", ev => {
        mouseX = ev.clientX;
        mouseY = ev.clientY;
    });

    let fadeLightning = false;
    let fadeStart = 0;

// utilities
    function center(el) {
        const r = el.getBoundingClientRect();
        return [(r.left + r.right) / 2, (r.top + r.bottom) / 2];
    }

    function lengthBasedSegments(x1, y1, x2, y2) {
        const L = Math.hypot(x2 - x1, y2 - y1);
        return Math.max(5, Math.round(L * 0.12));
    }

    function createLightningPolyline(x1, y1, x2, y2) {
        const segments = lengthBasedSegments(x1, y1, x2, y2);
        const dx = (x2 - x1) / segments, dy = (y2 - y1) / segments;
        const points = [];
        for (let i = 0; i <= segments; i++) {
            const nx = x1 + dx * i;
            const ny = y1 + dy * i;
            const offsetX = (i !== 0 && i !== segments) ? (Math.random() - 0.5) * 10 : 0;
            const offsetY = (i !== 0 && i !== segments) ? (Math.random() - 0.5) * 10 : 0;
            points.push(`${nx + offsetX},${ny + offsetY}`);
        }
        const poly = document.createElementNS(NS, "polyline");
        poly.setAttribute("points", points.join(" "));
        poly.setAttribute("stroke", accentColor);
        poly.setAttribute("stroke-width", "2");
        poly.setAttribute("fill", "none");
        poly.setAttribute("stroke-linecap", "round");
        poly.setAttribute("stroke-linejoin", "round");
        return poly;
    }

// animate all lightning lines
    function animate() {
        svg.innerHTML = ""; // clear previous frame


        const positions = picked.map(center);
        if (!fadeLightning && picked.length < 3 && picked.length > 0) {
            positions.push([mouseX, mouseY]);
        }

        // draw lines between consecutive positions
        for (let i = 0; i < positions.length - 1; i++) {
            const [x1, y1] = positions[i];
            const [x2, y2] = positions[i + 1];
            svg.appendChild(createLightningPolyline(x1, y1, x2, y2));

            // if this is the last segment and we have 3 points, draw a second parallel line
            if (i === 1 && positions.length === 3) {
                svg.appendChild(createLightningPolyline(x1, y1, x2, y2));
            }
        }

        // animate flicker by slightly randomizing points
        svg.querySelectorAll("polyline").forEach(poly => {
            const pts = poly.getAttribute("points").split(" ").map(pt => pt.split(",").map(Number));
            for (let i = 1; i < pts.length - 1; i++) {
                pts[i][0] += (Math.random() - 0.5) * 2;
                pts[i][1] += (Math.random() - 0.5) * 2;
            }
            poly.setAttribute("points", pts.map(p => p.join(",")).join(" "));
        });

        // fade effect
        if (fadeLightning) {
            const now = performance.now();
            const elapsed = now - fadeStart;
            let opacity = 1 - elapsed / 1000;
            if (opacity < 0) opacity = 0;
            svg.style.opacity = opacity;
            if (opacity === 0) {
                svg.innerHTML = "";
                svg.style.opacity = 1;
                fadeLightning = false;
                picked = [];
            }
        }

        requestAnimationFrame(animate);
    }

    animate();

// click handler
    document.addEventListener("click", ev => {
        const el = ev.target.closest(".connectable");
        if (!el) return;

        if (!el.classList.contains("selected")) {
            if (picked.length === 3) return;
            el.classList.add("selected");
            picked.push(el);
        } else {
            el.classList.remove("selected");
            picked = picked.filter(x => x !== el);
            return;
        }

        if (picked.length === 3) {
            // send selection to server
            fetch("/doroll", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf_token
                },
                body: JSON.stringify(picked.map(x => x.textContent.trim()))
            }).then(res => {
                if (!res.ok) return res.json().then(errData => {
                    throw new Error(errData.message);
                });
                return res.json();
            })
                .then(data => console.log("Server response:", data))
                .catch(err => alert("Failed: " + err.message));

            fadeLightning = true;
            fadeStart = performance.now();

            picked.forEach(x => x.classList.remove("selected"));
        }
    });


})
