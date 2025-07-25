let nodes = []

function makelabels() {
    const elements = [...document.querySelectorAll("[data-cyberlabel]")];

    nodes = elements.map((el, i) => {
        const label = document.createElement("div");
        label.className = "cyber-label";
        label.innerText = el.dataset.cyberlabel;
        Object.assign(label.style, {
            position: "absolute",
            left: "0px",
            top: "0px"
        });
        el.parentElement.classList.add("hoverparent");
        el.appendChild(label);
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        Object.assign(svg.style, {
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            overflow: "visible",
            pointerEvents: "none"
        });

        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        svg.classList.add("cyber-line")
        svg.appendChild(line);
        el.appendChild(svg);
        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        dot.setAttribute("r", "3");
        dot.setAttribute("fill", "red");

        svg.appendChild(dot);

        const rect = el.getBoundingClientRect();
        return {
            el, label, svg, line, dot,
            cx: rect.width / 2,
            cy: rect.height / 2,
            x: rect.width / 2 + Math.random() * 40 - 20,
            y: rect.height / 2 + Math.random() * 40 - 20,
            vx: 0,
            vy: 0
        };
    });

    for (let i = 0; i < 50; i++) {
        applyForces();
        render()
    }
}

function applyLabelRepulsion(repulsion = 8000, minDist = 20) {
    for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        const r1 = n1.label.getBoundingClientRect();
        const x1 = r1.left + r1.width / 2;
        const y1 = r1.top + r1.height / 2;

        for (let j = i + 1; j < nodes.length; j++) {
            const n2 = nodes[j];
            const r2 = n2.label.getBoundingClientRect();
            const x2 = r2.left + r2.width / 2;
            const y2 = r2.top + r2.height / 2;

            let dx = x2 - x1;
            let dy = y2 - y1;
            let dist = Math.max(Math.sqrt(dx * dx + dy * dy), minDist);
            let force = repulsion / (dist * dist);
            let fx = force * dx / dist;
            let fy = force * dy / dist;

            n1.vx -= fx;
            n1.vy -= fy;
            n2.vx += fx;
            n2.vy += fy;
        }
    }
}

function applyTargetRepulsion(repulsion = 8000, minDist = 20) {
    for (let node of nodes) {
        for (let targetNode of nodes) {
            let dx = node.x - targetNode.cx;
            let dy = node.y - targetNode.cy;
            let dist = Math.max(Math.sqrt(dx * dx + dy * dy), minDist);
            let force = repulsion / (dist * dist);
            node.vx += (dx / dist) * force * 0.1;
            node.vy += (dy / dist) * force * 0.1;
        }
    }
}

function applyMouseRepulsion(mouseStrength = 8000) {
    if (!mouse.active) return;

    for (let node of nodes) {
        const rect = node.el.getBoundingClientRect();
        const mx = mouse.x - rect.left;
        const my = mouse.y - rect.top;

        const dx = node.x - mx;
        const dy = node.y - my;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
        const force = mouseStrength / (dist * dist);

        node.vx += (dx / dist) * force;
        node.vy += (dy / dist) * force;
    }
}

function applySpringAndDamping(spring = 0.01, damping = 0.7) {
    for (let node of nodes) {
        let dx = node.cx - node.x;
        let dy = node.cy - node.y;
        node.vx += dx * spring;
        node.vy += dy * spring;

        node.vx *= damping;
        node.vy *= damping;

        node.x += node.vx;
        node.y += node.vy;
    }
}

function updatePositions() {
    let moved = false;
    for (let node of nodes) {
        if (!('lastX' in node)) {
            node.lastX = node.x;
            node.lastY = node.y;
        }
        const dx = node.x - node.lastX;
        const dy = node.y - node.lastY;
        if (Math.abs(dx) >= 1 || Math.abs(dy) >= 1) {
            moved = true;
            node.lastX = node.x;
            node.lastY = node.y;
        }
    }
    return moved;
}

function applyForces() {
    applyLabelRepulsion();
    applyTargetRepulsion();
    applyMouseRepulsion();
    applySpringAndDamping();
}


const mouse = {x: 0, y: 0, active: false};

document.addEventListener("mousemove", (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
    mouse.active = true;
});

document.addEventListener("mouseleave", () => {
    mouse.active = false;
});

function render() {
    for (let node of nodes) {
        const labelBox = node.label.getBoundingClientRect();

        const w = labelBox.width;
        const h = labelBox.height;

        const cx = node.cx;
        const cy = node.cy;

        const labelCenterX = node.x + w / 2;
        const labelCenterY = node.y + h / 2;

        const dx = cx - labelCenterX;
        const dy = cy - labelCenterY;
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1);

        const ux = dx / dist;
        const uy = dy / dist;

        const edgeX = labelCenterX + ux * (w / 2);
        const edgeY = labelCenterY + uy * (h / 2);

        // Position label at top-left corner
        node.label.style.transform = `translate(${node.x}px, ${node.y}px)`;

        // Update debug dot at label center
        node.dot.setAttribute("cx", labelCenterX);
        node.dot.setAttribute("cy", labelCenterY);

        // Update line from label edge to parent center
        node.line.setAttribute("x1", edgeX);
        node.line.setAttribute("y1", edgeY);
        node.line.setAttribute("x2", cx);
        node.line.setAttribute("y2", cy);
    }
}

function updateNodeCenters() {
    for (const node of nodes) {
        const rect = node.el.getBoundingClientRect();
        node.cx = rect.width / 2;
        node.cy = rect.height / 2;
    }
}

function tick() {
    updateNodeCenters()
    applyForces();
    if (updatePositions()) render();
    requestAnimationFrame(tick);
}

tick();


window.addEventListener('DOMContentLoaded', () => {
    let settleTimer = null;
    document.body.addEventListener('htmx:afterSettle', () => {
        clearTimeout(settleTimer);
        settleTimer = setTimeout(() => {
            makelabels();
        }, 500);
    });

    makelabels();

    document.body.addEventListener('htmx:afterSwap', () => {
        document.querySelectorAll('.hoverparent').forEach(parent => {
            parent.addEventListener('mouseenter', () => {
                parent.classList.add('fadeout-active');
            }, {once: true});
        });
    });

});
