let nodes = []

function makelabels() {
    const elements = [...document.querySelectorAll("[data-cyberlabel]")];
    nodes = [];

    // Group elements by their parent container (e.g., .meter)
    const containers = new Set();
    elements.forEach(el => containers.add(el.parentElement));

    containers.forEach(container => {
        container.classList.add("hoverparent");
        // Find or create an SVG layer for lines inside the container
        let svgLayer = container.querySelector(".cyber-svg-layer");
        if (!svgLayer) {
            svgLayer = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svgLayer.classList.add("cyber-svg-layer", "cyber-line");
            Object.assign(svgLayer.style, {
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                overflow: "visible",
                pointerEvents: "none"
            });
            container.appendChild(svgLayer);
        } else {
            svgLayer.innerHTML = ""; // Clear old lines
        }

        // Remove old labels from this container
        container.querySelectorAll(".cyber-label").forEach(l => l.remove());

        const segments = elements.filter(el => el.parentElement === container);
        const containerRect = container.getBoundingClientRect();

        segments.forEach((el, i) => {
            const fill = parseFloat(getComputedStyle(el).getPropertyValue('--fill')) || 0;
            // Only create labels for segments with non-zero fill
            if (fill === 0) return;

            const label = document.createElement("div");
            label.className = "cyber-label";
            label.innerText = el.dataset.cyberlabel;
            container.appendChild(label);

            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            svgLayer.appendChild(line);

            const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            dot.setAttribute("r", "3");
            svgLayer.appendChild(dot);

            const rect = el.getBoundingClientRect();
            // Target center relative to container
            const cx = (rect.left - containerRect.left) + rect.width / 2;
            const cy = (rect.top - containerRect.top) + rect.height / 2;

            nodes.push({
                el, label, line, dot, container,
                cx, cy,
                x: cx + (Math.random() - 0.5) * 50,
                y: cy + (Math.random() - 0.5) * 50,
                vx: 0, vy: 0,
                w: 0, h: 0 // Will be set in render
            });
        });
    });

    // Initial settle
    for (let i = 0; i < 100; i++) {
        applyForces();
        updatePositions();
    }
    render();
}

function applyLabelRepulsion(repulsion = 6000, minDist = 40) {
    for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
            const n2 = nodes[j];
            if (n1.container !== n2.container) continue;

            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            const distSq = dx * dx + dy * dy;
            const dist = Math.sqrt(distSq);

            if (dist < 200) {
                const force = repulsion / Math.max(distSq, minDist * minDist);
                const fx = (dx / (dist || 1)) * force;
                const fy = (dy / (dist || 1)) * force;
                n1.vx -= fx; n1.vy -= fy;
                n2.vx += fx; n2.vy += fy;
            }
        }
    }
}

function applyTargetRepulsion(repulsion = 10000) {
    for (let node of nodes) {
        const dx = node.x - node.cx;
        const dy = node.y - node.cy;
        const distSq = dx * dx + dy * dy;
        const dist = Math.sqrt(distSq);

        // Much wider push-away from the source bar (Classic floating feel)
        if (dist < 150) {
            const force = repulsion / Math.max(distSq, 400);
            node.vx += (dx / (dist || 1)) * force;
            node.vy += (dy / (dist || 1)) * force;
        }
    }
}

const mouse = { x: 0, y: 0, active: false };
document.addEventListener("mousemove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;
});
document.addEventListener("mouseleave", () => { mouse.active = false; });

function applyMouseRepulsion(strength = 5000) {
    if (!mouse.active) return;
    for (let node of nodes) {
        const cRect = node.container.getBoundingClientRect();
        const mx = mouse.x - cRect.left;
        const my = mouse.y - cRect.top;

        const dx = node.x - mx;
        const dy = node.y - my;
        const distSq = dx * dx + dy * dy;
        const dist = Math.sqrt(distSq);

        if (dist < 100) {
            const force = strength / Math.max(distSq, 100);
            node.vx += (dx / (dist || 1)) * force;
            node.vy += (dy / (dist || 1)) * force;
        }
    }
}

function applyBoundaryForces(margin = 15, strength = 0.5) {
    for (let node of nodes) {
        const cRect = node.container.getBoundingClientRect();
        // Repel from container edges (horizontal)
        if (node.x < margin) node.vx += (margin - node.x) * strength;
        if (node.x + node.w > cRect.width - margin) node.vx -= (node.x + node.w - (cRect.width - margin)) * strength;

        // Vertical window bounds (labels can float above/below the bar)
        const globalY = cRect.top + node.y;
        if (globalY < margin) node.vy += (margin - globalY) * strength;
        if (globalY + node.h > window.innerHeight - margin) node.vy -= (globalY + node.h - (window.innerHeight - margin)) * strength;
    }
}

function applySpringAndDamping(spring = 0.012, damping = 0.6) {
    for (let node of nodes) {
        // Pull back to target if far
        const dx = node.cx - node.x;
        const dy = node.cy - node.y;
        node.vx += dx * spring;
        node.vy += dy * spring;

        node.vx *= damping;
        node.vy *= damping;

        // Cap velocity
        const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
        if (speed > 10) {
            node.vx = (node.vx / speed) * 10;
            node.vy = (node.vy / speed) * 10;
        }

        node.x += node.vx;
        node.y += node.vy;
    }
}

function applyForces() {
    applyLabelRepulsion();
    applyTargetRepulsion();
    applyMouseRepulsion();
    applyBoundaryForces();
    applySpringAndDamping();
}

function updatePositions() {
    let moved = false;
    for (let node of nodes) {
        // Lower threshold for "stopped" to prevent micro-jitter
        if (Math.abs(node.vx) > 0.05 || Math.abs(node.vy) > 0.05) moved = true;
    }
    return moved;
}

function render() {
    for (let node of nodes) {
        const w = node.label.offsetWidth;
        const h = node.label.offsetHeight;
        node.w = w; node.h = h;

        const lx = node.x;
        const ly = node.y;

        // Connector line logic
        const targetX = node.cx;
        const targetY = node.cy;

        const centerX = lx + w / 2;
        const centerY = ly + h / 2;

        const dx = targetX - centerX;
        const dy = targetY - centerY;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        // Edge of label box for connection
        const ex = centerX + (dx / dist) * (w / 2);
        const ey = centerY + (dy / dist) * (h / 2);

        node.label.style.transform = `translate(${lx}px, ${ly}px)`;
        node.line.setAttribute("x1", ex);
        node.line.setAttribute("y1", ey);
        node.line.setAttribute("x2", targetX);
        node.line.setAttribute("y2", targetY);

        node.dot.setAttribute("cx", centerX);
        node.dot.setAttribute("cy", centerY);
    }
}

function tick() {
    applyForces();
    if (updatePositions()) render();
    requestAnimationFrame(tick);
}

tick();

window.addEventListener('resize', () => {
    // Re-anchor target positions on resize
    nodes.forEach(node => {
        const cRect = node.container.getBoundingClientRect();
        const eRect = node.el.getBoundingClientRect();
        node.cx = (eRect.left - cRect.left) + eRect.width / 2;
        node.cy = (eRect.top - cRect.top) + eRect.height / 2;
    });
});

window.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('htmx:afterSettle', () => {
        setTimeout(makelabels, 100);
    });
    makelabels();
});

function init_speed_graph(root = document) {
    const svg = root.querySelector("#speed-graph");
    if (!svg) return;

    const cursor = svg.querySelector("#cursor-line");
    const tooltip = svg.querySelector("#tooltip");
    const title = svg.querySelector("#tooltip-title");
    const value = svg.querySelector("#tooltip-value");

    const margin = 40;
    const graph_w = svg.viewBox.baseVal.width - 2 * margin;
    const max_time = parseFloat(svg.dataset.maxTime);

    svg.onmousemove = ev => {
        const pt = svg.createSVGPoint();
        pt.x = ev.clientX;
        pt.y = ev.clientY;
        const c = pt.matrixTransform(svg.getScreenCTM().inverse());

        if (c.x < margin || c.x > margin + graph_w) {
            tooltip.setAttribute("visibility", "hidden");
            cursor.setAttribute("visibility", "hidden");
            return;
        }

        cursor.setAttribute("visibility", "visible");
        cursor.setAttribute("x1", c.x);
        cursor.setAttribute("x2", c.x);

        const t = (c.x - margin) / graph_w * max_time;
        const out = [];

        svg.querySelectorAll(".curve-group").forEach(g => {
            if (g.classList.contains("hidden")) return;

            const name = g.dataset.name;
            const speeds = JSON.parse(g.dataset.speeds);

            const keys = Object.keys(speeds).map(Number).sort((a, b) => a - b);

            let k0 = keys[0];
            let k1 = keys[keys.length - 1];

            // find the segment that contains t
            for (let i = 0; i < keys.length - 1; i++) {
                if (t >= keys[i] && t <= keys[i + 1]) {
                    k0 = keys[i];
                    k1 = keys[i + 1];
                    break;
                }
            }
            if (t >= keys[keys.length - 1]) {
                const lastVal = speeds[keys[keys.length - 1]];
                out.push(`${name}: ${lastVal.toFixed(2)}`);
                return;
            }
            const v0 = speeds[k0];
            const v1 = speeds[k1];
            const ratio = (t - k0) / (k1 - k0);
            const v = v0 + (v1 - v0) * ratio;

            out.push(`${name}: ${v.toFixed(2)}`);
        });


        const offsetX = 12; // SVG units
        const offsetY = -4;

        tooltip.setAttribute("transform", `translate(${c.x + offsetX},${c.y + offsetY})`);
        const rect = tooltip.getBoundingClientRect();
        let dx = 0, dy = 0;
        if (rect.right > window.innerWidth) dx = window.innerWidth - rect.right;
        if (rect.top < 0) dy = -rect.top;
        tooltip.setAttribute("transform", `translate(${c.x + offsetX + dx},${c.y + offsetY + dy})`);
        tooltip.setAttribute("visibility", "visible");
        title.textContent = `t = ${t.toFixed(2)} s`;
        value.innerHTML = "";
        out.forEach((line, i) => {
            const tsp = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
            tsp.setAttribute("x", 12);          // relative to tooltip <text>
            tsp.setAttribute("dy", i === 0 ? "1.2em" : "1.2em");
            tsp.textContent = line;
            value.appendChild(tsp);
        });
    };

    svg.onmouseleave = () => {
        tooltip.setAttribute("visibility", "hidden");
        cursor.setAttribute("visibility", "hidden");
    };

    svg.querySelectorAll(".legend-item").forEach(label => {
        label.onclick = () => {
            const g = label.closest(".curve-group");
            g.classList.toggle("hidden");
            g.classList.toggle("active");
        };
    });
}


document.addEventListener("DOMContentLoaded", () => {
    init_speed_graph(document);
    document.body.addEventListener("htmx:afterSwap", e => {
        init_speed_graph(e.target);
    });
});
