// --- Turn Management (Clientside Pending) ---
window.mechaState = {
    identifier: '',
    baseTurn: 0,
    baseFluxPool: 0,
    baseFluxPoolMax: 0,
    systems: {}, 
    pending: {
        speed: null,
        toggles: {}, 
        heat: {},    
        loadout: null,
        heat_manual: 0
    },
    loadouts: {}
};

window.initMechaState = function(identifier, turn, pool, max) {
    window.mechaState.identifier = identifier;
    window.mechaState.baseTurn = parseInt(turn);
    window.mechaState.baseFluxPool = parseFloat(pool);
    window.mechaState.baseFluxPoolMax = parseFloat(max);
    console.log('DEBUG: Mecha state initialized:', identifier, turn, pool, max);
}

window.registerSystem = function(b64Name, name, type, current, capacity, flux, energy, heat, active) {
    window.mechaState.systems[b64Name] = {
        name: name,
        type: type,
        current: parseFloat(current),
        capacity: parseFloat(capacity),
        flux: parseFloat(flux),
        energy: parseFloat(energy),
        heat: parseFloat(heat),
        active: active === true || active === "true"
    };
}

window.updateSpeedUI = function() {
    if (window.mechaState.pending.speed !== null) {
        const sidebarSpeed = document.querySelector('#sidebar-speed .highlight');
        if (sidebarSpeed) {
            sidebarSpeed.innerText = window.mechaState.pending.speed.toFixed(1);
        }
    }
}

window.updateHeatUI = function() {
    let currentPool = window.mechaState.baseFluxPool;
    
    for (let b64 in window.mechaState.pending.heat) {
        const sys = window.mechaState.systems[b64];
        if (sys) {
            const delta = window.mechaState.pending.heat[b64] - sys.current;
            currentPool -= delta;
        }
    }

    const poolVal = document.querySelector('.flux-value');
    if (poolVal) {
        poolVal.innerText = currentPool.toFixed(1) + ' / ' + window.mechaState.baseFluxPoolMax.toFixed(1);
    }
    
    const poolFill = document.querySelector('.flux-bar-fill');
    if (poolFill) {
        const percent = (currentPool / window.mechaState.baseFluxPoolMax) * 100;
        poolFill.style.width = Math.min(100, Math.max(0, percent)) + '%';
        poolFill.style.backgroundColor = currentPool < 0 ? 'var(--danger)' : 'var(--accent)';
    }
    
    // Update sidebar summary
    const sidebarFlux = document.querySelector('#sidebar-heat .highlight');
    if (sidebarFlux) {
        sidebarFlux.innerText = currentPool.toFixed(1) + ' / ' + window.mechaState.baseFluxPoolMax.toFixed(1);
    }
    
    window.updateNextTurnBreakdown();
}

window.onHeatSliderInput = function(el, b64Name) {
    const newVal = parseFloat(el.value);
    console.log('DEBUG: onHeatSliderInput:', b64Name, newVal);
    const sys = window.mechaState.systems[b64Name];
    if (!sys) return;
    
    // Calculate total pending delta excluding THIS system
    let otherPendingDelta = 0;
    for (let otherB64 in window.mechaState.pending.heat) {
        if (otherB64 !== b64Name) {
            otherPendingDelta += (window.mechaState.pending.heat[otherB64] - window.mechaState.systems[otherB64].current);
        }
    }
    
    const poolBeforeThis = window.mechaState.baseFluxPool - otherPendingDelta;
    const currentDelta = newVal - sys.current;
    
    // Constraint: Pool cannot go under 0
    if (currentDelta > poolBeforeThis + 0.001) {
        const allowedNewVal = sys.current + poolBeforeThis;
        el.value = allowedNewVal;
        return window.onHeatSliderInput(el, b64Name);
    }

    // Constraint: Pool cannot go over Max (unless already over)
    const max = window.mechaState.baseFluxPoolMax;
    const newPool = poolBeforeThis - currentDelta;
    
    if (newPool > max + 0.001) {
        if (newPool > poolBeforeThis + 0.001 || poolBeforeThis <= max) {
             const allowedNewVal = sys.current + (poolBeforeThis - max);
             el.value = Math.max(el.min, allowedNewVal);
             return window.onHeatSliderInput(el, b64Name);
        }
    }

    window.mechaState.pending.heat[b64Name] = parseFloat(el.value);

    const card = document.getElementById('system-' + b64Name);
    if (card) {
        const storageDisplay = card.querySelector('.heat-assignment-ui .highlight');
        if (storageDisplay) {
            storageDisplay.innerText = window.mechaState.pending.heat[b64Name].toFixed(1) + ' / ' + sys.capacity.toFixed(1);
        }
    }

    window.updateHeatUI();
}

window.onSystemToggle = function(b64Name) {
    const sys = window.mechaState.systems[b64Name];
    if (!sys) return;
    
    if (window.mechaState.pending.toggles[b64Name] !== undefined) {
        delete window.mechaState.pending.toggles[b64Name];
    } else {
        window.mechaState.pending.toggles[b64Name] = !sys.active;
    }
    
    const card = document.getElementById('system-' + b64Name);
    if (card) {
        const btn = card.querySelector('.control-btn');
        const willBeActive = window.mechaState.pending.toggles[b64Name] !== undefined ? window.mechaState.pending.toggles[b64Name] : sys.active;
        if (btn) btn.innerText = willBeActive ? 'DEACTIVATE' : 'ACTIVATE';
        card.className = 'system-card ' + (willBeActive ? 'state-active' : 'state-offline');
    }
    
    window.updateHeatUI();
    window.updateNextTurnBreakdown();
}

window.updateNextTurnBreakdown = function() {
    const list = document.getElementById('pending-changes-list');
    if (!list) return;
    
    list.innerHTML = '';
    let hasChanges = false;
    
    if (window.mechaState.pending.speed !== null) {
        addPendingItem(list, 'Set Target Speed to ' + window.mechaState.pending.speed.toFixed(1) + ' km/h', () => { window.mechaState.pending.speed = null; window.updateNextTurnBreakdown(); });
        hasChanges = true;
    }
    
    if (window.mechaState.pending.loadout !== null) {
        addPendingItem(list, 'Apply Loadout: ' + window.mechaState.pending.loadout, () => { window.mechaState.pending.loadout = null; window.updateNextTurnBreakdown(); });
        hasChanges = true;
    }
    
    for (let b64 in window.mechaState.pending.toggles) {
        const sys = window.mechaState.systems[b64];
        if (!sys) continue;
        const state = window.mechaState.pending.toggles[b64] ? 'active' : 'inactive';
        addPendingItem(list, 'Toggle ' + sys.name + ' to ' + state, () => { 
            delete window.mechaState.pending.toggles[b64]; 
            const card = document.getElementById('system-' + b64);
            if (card) {
                const btn = card.querySelector('.control-btn');
                if (btn) btn.innerText = sys.active ? 'DEACTIVATE' : 'ACTIVATE';
                card.className = 'system-card ' + (sys.active ? 'state-active' : 'state-offline');
            }
            window.updateNextTurnBreakdown(); 
        });
        hasChanges = true;
    }
    
    for (let b64 in window.mechaState.pending.heat) {
        const sys = window.mechaState.systems[b64];
        if (!sys) continue;
        const val = window.mechaState.pending.heat[b64];
        if (Math.abs(val - sys.current) > 0.001) {
            addPendingItem(list, 'Assign ' + val.toFixed(1) + ' total heat to ' + sys.name, () => { 
                delete window.mechaState.pending.heat[b64]; 
                const card = document.getElementById('system-' + b64);
                if (card) {
                    const slider = card.querySelector('input[type="range"]');
                    if (slider) slider.value = sys.current;
                    const storageDisplay = card.querySelector('.heat-assignment-ui .highlight');
                    if (storageDisplay) storageDisplay.innerText = sys.current.toFixed(1) + ' / ' + sys.capacity.toFixed(1);
                }
                window.updateHeatUI(); 
            });
            hasChanges = true;
        }
    }

    if (window.mechaState.pending.heat_manual && Math.abs(window.mechaState.pending.heat_manual) > 0.001) {
        addPendingItem(list, 'Manual Heat Adjustment: ' + window.mechaState.pending.heat_manual.toFixed(1), () => { window.mechaState.pending.heat_manual = 0; window.updateNextTurnBreakdown(); });
        hasChanges = true;
    }
    
    if (!hasChanges) {
        list.innerHTML = '<p style="color: var(--text-dim); font-style: italic;">No pending changes for Turn ' + (window.mechaState.baseTurn + 1) + '</p>';
    }
    
    window.updateForecastDisplays();
}

function addPendingItem(parent, text, onRemove) {
    const div = document.createElement('div');
    div.className = 'pending-item';
    div.style = 'margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 5px;';
    div.innerHTML = '<span>' + text + '</span>';
    
    const btn = document.createElement('button');
    btn.className = 'control-btn';
    btn.style = 'padding: 2px 10px; font-size: 0.7em;';
    btn.innerText = 'REMOVE';
    btn.onclick = onRemove;
    
    div.appendChild(btn);
    parent.appendChild(div);
}

window.updateForecastDisplays = function() {
    let genFlux = 0;
    let energyOutput = 0;
    let energyDemand = 0;
    
    let items = [];
    
    const activeLoadout = window.mechaState.pending.loadout;
    const loadoutSystems = activeLoadout ? window.mechaState.loadouts[activeLoadout] : null;

    for (let b64 in window.mechaState.systems) {
        const sys = window.mechaState.systems[b64];
        let willBeActive = sys.active;
        if (activeLoadout && loadoutSystems) {
            willBeActive = loadoutSystems.includes(b64);
        } else if (window.mechaState.pending.toggles[b64] !== undefined) {
            willBeActive = window.mechaState.pending.toggles[b64];
        }
        
        if (willBeActive) {
            genFlux += sys.heat;
            if (sys.heat > 0) {
                items.push({ name: sys.name, type: sys.type, heat: sys.heat });
            }
            if (sys.type === 'energy') {
                energyOutput += sys.energy;
            } else {
                energyDemand += sys.energy;
            }
        }
    }

    if (window.mechaState.pending.heat_manual) {
        genFlux += window.mechaState.pending.heat_manual;
    }
    
    const forecastText = document.getElementById('js-projected-heat');
    if (forecastText) forecastText.innerText = "+" + genFlux.toFixed(1) + " Flux";
    
    const heatTabForecast = document.getElementById('js-heat-forecast-val');
    if (heatTabForecast) heatTabForecast.innerText = "+" + genFlux.toFixed(1) + " Flux";

    const breakdown = document.getElementById('js-forecast-breakdown');
    if (breakdown) {
        breakdown.innerHTML = "";
        items.forEach(item => {
            const div = document.createElement('div');
            div.style = "display: flex; justify-content: space-between; opacity: 0.8; padding: 2px 5px; background: rgba(255,255,255,0.03); border-radius: 2px;";
            div.innerHTML = `<span><span style="opacity: 0.5;">[${item.type[0].toUpperCase()}]</span> ${item.name}</span><span class="highlight">+${item.heat.toFixed(1)}</span>`;
            breakdown.appendChild(div);
        });
    }
    
    const bar = document.getElementById('js-forecast-bar');
    if (bar) {
        const maxF = window.mechaState.baseFluxPoolMax;
        bar.style.width = Math.min(100, (genFlux / maxF) * 100) + "%";
        bar.style.backgroundColor = genFlux > maxF ? "var(--danger)" : "var(--primary)";
    }
    
    const heatBar = document.getElementById('js-heat-forecast-bar');
    if (heatBar) {
        const maxF = window.mechaState.baseFluxPoolMax;
        heatBar.style.width = Math.min(100, (genFlux / maxF) * 100) + "%";
        heatBar.style.backgroundColor = genFlux > maxF ? "var(--danger)" : "var(--primary)";
    }
    
    const warning = document.getElementById('js-overheat-warning');
    if (warning) warning.innerHTML = genFlux > window.mechaState.baseFluxPoolMax ? '<p style="color: var(--danger); font-size: 0.7em; margin-top: 10px; font-style: italic;">OVERHEAT RISK</p>' : '';

    const heatWarning = document.getElementById('js-heat-forecast-warning');
    if (heatWarning) heatWarning.innerHTML = genFlux > window.mechaState.baseFluxPoolMax ? '<p style="color: var(--danger); font-size: 0.8em; margin-top: 8px; font-style: italic;">WARNING: Generation exceeds transfer capacity (' + window.mechaState.baseFluxPoolMax.toFixed(1) + '). Overheat imminent!</p>' : '';

    const outText = document.getElementById('js-energy-output');
    if (outText) outText.innerText = energyOutput.toFixed(1);
    
    const demText = document.getElementById('js-energy-demand');
    if (demText) demText.innerText = energyDemand.toFixed(1);
}

window.commitTurn = function() {
    console.log('DEBUG: commitTurn() called');
    const url = '/mecha_commit_turn/' + window.mechaState.identifier;
    const data = JSON.stringify(window.mechaState.pending);
    
    return fetch(url, {
        method: 'POST',
        body: data,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    }).then(response => {
        if (response.ok) {
            window.location.reload();
        }
    });
}

window.onLoadoutChange = function(el) {
    window.mechaState.pending.loadout = el.value;
    window.updateNextTurnBreakdown();
}

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

window.switchTab = function(tabId, el) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    el.classList.add('active');
    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
    const targetPanel = document.getElementById('view-' + tabId);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }
    const titles = {
        'overview': 'MECHA OVERVIEW',
        'movement': 'NAVIGATION & PROPULSION',
        'energy': 'REACTOR & ENERGY SYSTEMS',
        'heat': 'THERMAL MANAGEMENT',
        'combat': 'COMBAT SYSTEMS',
        'nextturn': 'TURN TRANSITION',
        'timeline': 'ENCOUNTER TIMELINE'
    };
    const mainTitle = document.getElementById('main-title');
    if (mainTitle && titles[tabId]) {
        mainTitle.innerText = titles[tabId];
    }
}

window.makelabels = function() {
    const elements = [...document.querySelectorAll("[data-cyberlabel]")];
    const nodes = [];
    const containers = new Set();
    elements.forEach(el => containers.add(el.parentElement));
    containers.forEach(container => {
        container.classList.add("hoverparent");
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
            svgLayer.innerHTML = ""; 
        }
        container.querySelectorAll(".cyber-label").forEach(l => l.remove());
        const segments = elements.filter(el => el.parentElement === container);
        const containerRect = container.getBoundingClientRect();
        segments.forEach((el, i) => {
            const fill = parseFloat(getComputedStyle(el).getPropertyValue('--fill')) || 0;
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
            const cx = (rect.left - containerRect.left) + rect.width / 2;
            const cy = (rect.top - containerRect.top) + rect.height / 2;
            nodes.push({
                el, label, line, dot, container,
                cx, cy,
                x: cx + (Math.random() - 0.5) * 50,
                y: cy + (Math.random() - 0.5) * 50,
                vx: 0, vy: 0,
                w: 0, h: 0 
            });
        });
    });
    
    function applyForces() {
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
                    const force = 6000 / Math.max(distSq, 1600);
                    const fx = (dx / (dist || 1)) * force;
                    const fy = (dy / (dist || 1)) * force;
                    n1.vx -= fx; n1.vy -= fy;
                    n2.vx += fx; n2.vy += fy;
                }
            }
        }
        for (let node of nodes) {
            const dx = node.x - node.cx;
            const dy = node.y - node.cy;
            const distSq = dx * dx + dy * dy;
            const dist = Math.sqrt(distSq);
            if (dist < 150) {
                const force = 10000 / Math.max(distSq, 400);
                node.vx += (dx / (dist || 1)) * force;
                node.vy += (dy / (dist || 1)) * force;
            }
            const cRect = node.container.getBoundingClientRect();
            if (node.x < 15) node.vx += (15 - node.x) * 0.5;
            if (node.x + node.w > cRect.width - 15) node.vx -= (node.x + node.w - (cRect.width - 15)) * 0.5;
            node.vx += (node.cx - node.x) * 0.012;
            node.vy += (node.cy - node.y) * 0.012;
            node.vx *= 0.6;
            node.vy *= 0.6;
            node.x += node.vx;
            node.y += node.vy;
        }
    }

    function render() {
        for (let node of nodes) {
            if (!node.label) continue;
            const w = node.label.offsetWidth;
            const h = node.label.offsetHeight;
            node.w = w; node.h = h;
            const centerX = node.x + w / 2;
            const centerY = node.y + h / 2;
            const dx = node.cx - centerX;
            const dy = node.cy - centerY;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const ex = centerX + (dx / dist) * (w / 2);
            const ey = centerY + (dy / dist) * (h / 2);
            node.label.style.transform = `translate(${node.x}px, ${node.y}px)`;
            node.line.setAttribute("x1", ex);
            node.line.setAttribute("y1", ey);
            node.line.setAttribute("x2", node.cx);
            node.line.setAttribute("y2", node.cy);
            node.dot.setAttribute("cx", centerX);
            node.dot.setAttribute("cy", centerY);
        }
    }

    function tick() {
        applyForces();
        render();
        requestAnimationFrame(tick);
    }
    tick();
}

window.addEventListener('resize', () => {
    // Refresh labels on resize
    window.makelabels();
});

window.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('htmx:afterSettle', () => {
        setTimeout(window.makelabels, 100);
    });
    window.makelabels();
});

window.init_speed_graph = function(root = document) {
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
        pt.x = ev.clientX; pt.y = ev.clientY;
        const c = pt.matrixTransform(svg.getScreenCTM().inverse());
        if (c.x < margin || c.x > margin + graph_w) {
            tooltip.setAttribute("visibility", "hidden");
            cursor.setAttribute("visibility", "hidden");
            return;
        }
        cursor.setAttribute("visibility", "visible");
        cursor.setAttribute("x1", c.x); cursor.setAttribute("x2", c.x);
        const t = (c.x - margin) / graph_w * max_time;
        const out = [];
        svg.querySelectorAll(".curve-group").forEach(g => {
            if (g.classList.contains("hidden")) return;
            const name = g.dataset.name;
            const speeds = JSON.parse(g.dataset.speeds);
            const keys = Object.keys(speeds).map(Number).sort((a, b) => a - b);
            let k0 = keys[0], k1 = keys[keys.length - 1];
            for (let i = 0; i < keys.length - 1; i++) {
                if (t >= keys[i] && t <= keys[i + 1]) { k0 = keys[i]; k1 = keys[i + 1]; break; }
            }
            if (t >= keys[keys.length - 1]) { out.push(`${name}: ${speeds[keys[keys.length - 1]].toFixed(2)}`); return; }
            const v0 = speeds[k0], v1 = speeds[k1];
            const v = v0 + (v1 - v0) * (t - k0) / (k1 - k0);
            out.push(`${name}: ${v.toFixed(2)}`);
        });
        tooltip.setAttribute("transform", `translate(${c.x + 12},${c.y - 4})`);
        tooltip.setAttribute("visibility", "visible");
        title.textContent = `t = ${t.toFixed(2)} s`;
        value.innerHTML = "";
        out.forEach((line, i) => {
            const tsp = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
            tsp.setAttribute("x", 12); tsp.setAttribute("dy", "1.2em");
            tsp.textContent = line; value.appendChild(tsp);
        });
    };
    svg.onmouseleave = () => { tooltip.setAttribute("visibility", "hidden"); cursor.setAttribute("visibility", "hidden"); };
    svg.querySelectorAll(".legend-item").forEach(label => {
        label.onclick = () => {
            const g = label.closest(".curve-group");
            g.classList.toggle("hidden"); g.classList.toggle("active");
        };
    });
}

document.addEventListener("DOMContentLoaded", () => {
    window.init_speed_graph(document);
    document.body.addEventListener("htmx:afterSwap", e => {
        window.init_speed_graph(e.target);
    });
});
