window.addEventListener("load", () => {
    const csrf_token = document.querySelector('meta[name="csrf-token"]').content;
    const accentColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--accent-color').trim();

    let picked = [];
    let rerollSign = null;
    let rerollValue = null;

    const svg = document.getElementById("conn-svg");
    const NS = "http://www.w3.org/2000/svg";

    let mouseX = 0, mouseY = 0;
    document.addEventListener("mousemove", ev => {
        mouseX = ev.clientX;
        mouseY = ev.clientY;
    });

    let lightningMode = false;
    const lightningToggle = document.getElementById('lightning-toggle');
    const numericOverrides = document.getElementById('numeric-overrides');
    const sequenceContainer = document.getElementById('lightning-sequence');
    const sendButton = document.getElementById('lightning-send');

    const rerollWrapper = document.getElementById('reroll-wrapper');
    const rerollToggle = document.getElementById('reroll-toggle');
    const rerollSelector = document.getElementById('reroll-selector');
    const rerollSignGroup = document.getElementById('reroll-sign-group');
    const rerollValGroup = document.getElementById('reroll-val-group');

    function resetLightningMode() {
        picked.forEach(item => item.el.classList.remove('selected'));
        picked = [];
        rerollSign = null;
        rerollValue = null;
        document.querySelectorAll('.reroll-sign-btn, .reroll-val-btn').forEach(b => b.classList.remove('selected'));
        if (rerollSelector) {
            rerollSelector.classList.remove('active');
            rerollSignGroup.style.display = 'flex';
            rerollValGroup.style.display = 'none';
        }
        if (rerollWrapper) rerollWrapper.style.display = 'none';
        if (sequenceContainer) sequenceContainer.innerHTML = '';
        if (sendButton) sendButton.style.display = 'none';
        const resultEl = document.getElementById('lightning-result');
        if (resultEl) {
            resultEl.classList.remove('active');
            setTimeout(() => { if(!resultEl.classList.contains('active')) resultEl.textContent = ''; }, 400);
        }
        fadeLightning = true;
        fadeStart = performance.now();
        lightningToggle.classList.remove('active');
        numericOverrides.classList.remove('active');
        document.body.classList.remove('lightning-active');
        document.querySelectorAll('.connectable').forEach(e => e.classList.remove('pulsing'));
    }

    function toggleLightningMode(force) {
        lightningMode = (force !== undefined) ? force : !lightningMode;
        lightningToggle.classList.toggle('active', lightningMode);
        numericOverrides.classList.toggle('active', lightningMode);
        document.body.classList.toggle('lightning-active', lightningMode);

        document.querySelectorAll('.connectable').forEach(el => {
            el.classList.toggle('pulsing', lightningMode);
        });

        if (!lightningMode) {
            resetLightningMode();
        }
    }

    if (lightningToggle) {
        lightningToggle.addEventListener('click', () => {
            toggleLightningMode();
        });
    }

    if (rerollToggle) {
        rerollToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            if (rerollSign || rerollValue) {
                rerollSign = null;
                rerollValue = null;
                document.querySelectorAll('.reroll-sign-btn, .reroll-val-btn').forEach(b => b.classList.remove('selected'));
                rerollSelector.classList.remove('active');
                rerollToggle.classList.remove('active');
                updateSequenceUI();
            } else {
                rerollSelector.classList.toggle('active');
                rerollToggle.classList.toggle('active', rerollSelector.classList.contains('active'));
                rerollSignGroup.style.display = 'flex';
                rerollValGroup.style.display = 'none';
            }
        });
    }

    document.querySelectorAll('.reroll-sign-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            rerollSign = btn.dataset.sign;
            document.querySelectorAll('.reroll-sign-btn').forEach(b => b.classList.toggle('selected', b === btn));
            rerollSignGroup.style.display = 'none';
            rerollValGroup.style.display = 'flex';
        });
    });

    document.querySelectorAll('.reroll-val-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            rerollValue = btn.dataset.val;
            document.querySelectorAll('.reroll-val-btn').forEach(b => b.classList.toggle('selected', b === btn));
            rerollSelector.classList.remove('active');
            rerollToggle.classList.remove('active');
            updateSequenceUI();
        });
    });

    function sendLightningRoll() {
        if (picked.length > 0) {
            const payload = picked.map(p => ({
                type: p.type,
                val: p.val,
                label: p.label,
                joiner: p.joiner
            }));
            if (rerollSign && rerollValue) {
                payload.push({
                    type: 'reroll',
                    val: `${rerollSign}${rerollValue}`,
                    label: `R${rerollSign}${rerollValue}`
                });
            }

            const resultEl = document.getElementById('lightning-result');
            if (resultEl) {
                resultEl.textContent = 'Rolling...';
                resultEl.classList.add('active');
            }

            fetch("/doroll", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf_token
                },
                body: JSON.stringify(payload)
            }).then(res => {
                if (!res.ok) return res.json().then(errData => {
                    throw new Error(errData.message);
                });
                return res.json();
            })
                .then(data => console.log("Server response:", data))
                .catch(err => alert("Failed: " + err.message));

            resetLightningMode();
            lightningMode = false;
        }
    }

    if (sendButton) {
        sendButton.addEventListener('click', sendLightningRoll);
    }

    document.addEventListener('keydown', (e) => {
        if (!lightningMode) return;

        if (e.code === 'Space' && picked.length > 0) {
            e.preventDefault();
            sendLightningRoll();
        } else if (e.code === 'Escape') {
            e.preventDefault();
            resetLightningMode();
            lightningMode = false;
        }
    });

    let fadeLightning = false;
    let fadeStart = 0;

    function center(el) {
        if (!el) {
            el = document.getElementById('lightning-toggle');
            if (!el) return [0, 0];
        }
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return [0, 0];
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

    function updateSequenceUI() {
        if (!sequenceContainer) return;
        sequenceContainer.innerHTML = '';

        picked.forEach((p, i) => {
            if (i > 0) {
                const sep = document.createElement('span');
                sep.className = 'sequence-separator interactive';
                sep.textContent = p.joiner;
                sep.onclick = (e) => {
                    e.stopPropagation();
                    p.joiner = p.joiner === ',' ? '+' : ',';
                    updateSequenceUI();
                };
                sequenceContainer.appendChild(sep);
                p.prevSeparator = sep;
            }
            const pickDiv = document.createElement('div');
            pickDiv.className = 'floating-pick';
            if (p.isNew) {
                pickDiv.classList.add('animate-in');
                delete p.isNew;
            }
            pickDiv.textContent = p.label;
            sequenceContainer.appendChild(pickDiv);
            p.floatingEl = pickDiv;
        });

        if (picked.length > 0) {
            const pendingSep = document.createElement('span');
            pendingSep.className = 'sequence-separator interactive pending';
            pendingSep.textContent = (picked.length === 1) ? ',' : '+';

            pendingSep.onclick = (e) => {
                e.stopPropagation();
                pendingSep.textContent = (pendingSep.textContent === ',') ? '+' : ',';
            };

            sequenceContainer.appendChild(pendingSep);
            sequenceContainer.pendingSeparator = pendingSep;
        }

        if (rerollSign && rerollValue) {
            if (rerollToggle) {
                rerollToggle.textContent = `R${rerollSign}${rerollValue}`;
                rerollToggle.classList.add('selected-reroll');
                rerollToggle.classList.add('active');
            }
        } else {
            if (rerollToggle) {
                rerollToggle.textContent = 'R';
                rerollToggle.classList.remove('selected-reroll');
                rerollToggle.classList.remove('active');
            }
        }

        const hasSelections = picked.length > 0;
        if (sendButton) sendButton.style.display = hasSelections ? 'flex' : 'none';
        if (rerollWrapper) rerollWrapper.style.display = hasSelections ? 'block' : 'none';
    }

    function animate() {
        if (!svg) return;
        svg.innerHTML = "";

        if (lightningMode) {
            picked.forEach((p) => {
                if (p.el && p.floatingEl) {
                    const p1 = center(p.el);
                    const p2 = center(p.floatingEl);
                    svg.appendChild(createLightningPolyline(p1[0], p1[1], p2[0], p2[1]));
                    svg.appendChild(createLightningPolyline(p1[0], p1[1], p2[0], p2[1]));
                }
            });

            if (!fadeLightning) {
                let targetPoint = [0, 0];
                if (sequenceContainer && sequenceContainer.pendingSeparator) {
                    targetPoint = center(sequenceContainer.pendingSeparator);
                }

                if (targetPoint[0] === 0 && targetPoint[1] === 0) {
                    targetPoint = center(lightningToggle);
                }

                if (targetPoint[0] !== 0 || targetPoint[1] !== 0) {
                    svg.appendChild(createLightningPolyline(targetPoint[0], targetPoint[1], mouseX, mouseY));
                }
            }
        }

        svg.querySelectorAll("polyline").forEach(poly => {
            const pts = poly.getAttribute("points").split(" ").map(pt => pt.split(",").map(Number));
            for (let i = 1; i < pts.length - 1; i++) {
                pts[i][0] += (Math.random() - 0.5) * 2;
                pts[i][1] += (Math.random() - 0.5) * 2;
            }
            poly.setAttribute("points", pts.map(p => p.join(",")).join(" "));
        });

        if (fadeLightning) {
            const now = performance.now();
            const elapsed = now - fadeStart;
            let opacity = 1 - elapsed / 500;
            if (opacity < 0) opacity = 0;
            svg.style.opacity = opacity;
            if (opacity === 0) {
                svg.innerHTML = "";
                svg.style.opacity = 1;
                fadeLightning = false;
            }
        }

        requestAnimationFrame(animate);
    }

    animate();

    function getNextJoiner(index) {
        return index === 1 ? ',' : '+';
    }

    document.addEventListener("click", ev => {
        const el = ev.target.closest(".connectable");
        const isFloating = ev.target.closest(".floating-pick");

        if (el && !lightningMode && !ev.target.closest('.nav-lightning')) {
            toggleLightningMode(true);
        }

        if (!lightningMode) {
            if (rerollSelector && rerollSelector.classList.contains('active')) {
                rerollSelector.classList.remove('active');
            }
            return;
        }

        if (rerollSelector && rerollSelector.classList.contains('active') && !ev.target.closest('#reroll-wrapper')) {
            rerollSelector.classList.remove('active');
        }

        if (isFloating) {
            const pickIndex = Array.from(sequenceContainer.querySelectorAll('.floating-pick')).indexOf(isFloating);
            if (pickIndex !== -1) {
                const item = picked[pickIndex];
                picked.splice(pickIndex, 1);

                if (!picked.some(p => p.el === item.el)) {
                    item.el.classList.remove('selected');
                }

                picked.forEach((p, idx) => {
                    if (idx > 0) p.joiner = getNextJoiner(idx);
                });
                updateSequenceUI();
            }
            return;
        }

        if (!el) return;

        const type = el.dataset.type || (el.classList.contains('numeric-btn') ? 'number' : 'stat');
        const val = el.dataset.val || el.textContent.trim();
        const label = el.dataset.label || el.textContent.trim();

        el.classList.add("selected");
        const newItem = {el, type, val, label};
        if (picked.length > 0) {
            newItem.joiner = getNextJoiner(picked.length);
        }
        newItem.isNew = true;
        picked.push(newItem);
        updateSequenceUI();
    });

    document.addEventListener('dblclick', ev => {
        if (lightningMode) {
            ev.preventDefault();
            ev.stopPropagation();
        }
    }, true);
});
