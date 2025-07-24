const offsets = [
    {dx: -1, dy: -1, label: 'top-left'},
    {dx: 1, dy: -1, label: 'top-right'},
    {dx: -1, dy: 1, label: 'bottom-left'},
    {dx: 1, dy: 1, label: 'bottom-right'}
];

function debugCandidate(candidate, color = 'blue', name = '') {
    // Draw candidate center
    const dot = document.createElement('div');
    dot.style.position = 'fixed';
    dot.style.left = `${candidate.x}px`;
    dot.style.top = `${candidate.y}px`;
    dot.style.width = '6px';
    dot.style.height = '6px';
    dot.style.backgroundColor = color;
    dot.style.borderRadius = '50%';
    dot.style.zIndex = 9999;
    dot.textContent = name;
    dot.style.color = 'white';
    dot.style.fontSize = '8px';
    dot.style.userSelect = 'none';
    dot.classList.add('debug-dot');
    document.body.appendChild(dot);

    // Draw label bounding box
    const rect = document.createElement('div');
    rect.style.position = 'fixed';
    rect.style.left = `${candidate.x}px`;
    rect.style.top = `${candidate.y}px`;
    rect.style.width = `${candidate.labelW}px`;
    rect.style.height = `${candidate.labelH}px`;
    rect.style.border = `1px solid ${color}`;
    rect.style.zIndex = 9998;
    rect.style.pointerEvents = 'none';
    rect.classList.add('debug-dot');
    document.body.appendChild(rect);
}

function clearDebug() {
    document.querySelectorAll('.debug-dot').forEach(el => el.remove());
}

function renderCyberlabels() {
    removeOldLabels();

    const labelDistance = 30;
    const elements = [...document.querySelectorAll('[data-cyberlabel]')];
    const allCandidates = [];

    elements.forEach(target => {
        const labelText = target.getAttribute('data-cyberlabel');
        const rect = target.getBoundingClientRect();
        const center = {x: rect.left + rect.width / 2, y: rect.top + rect.height / 2};

        const temp = document.createElement('div');
        temp.className = 'cyberlabel-label';
        temp.textContent = labelText;
        temp.style.position = 'absolute';
        temp.style.visibility = 'hidden';
        document.body.appendChild(temp);

        const labelW = temp.offsetWidth;
        const labelH = temp.offsetHeight;

        const candidates = offsets.map(({dx, dy}) => ({
            x: center.x + dx * (rect.height + labelDistance) - labelW / 2,
            y: center.y + dy * (rect.height + labelDistance) - labelH / 2,
            dx, dy,
            labelW, labelH,
            labelText,
            target,
            center
        }));

        allCandidates.push(...candidates);
        temp.remove();
    });

    const n = elements.length;

    // Greedy max-min selection of candidates
    const selected = [];
    selected.push(allCandidates[0]);

    function dist(a, b) {
        return Math.hypot(a.x - b.x, a.y - b.y);
    }

    while (selected.length < n) {
        let bestCandidate = null;
        let bestMinDist = -Infinity;

        for (const cand of allCandidates) {
            if (selected.includes(cand)) continue;
            const minDistToSelected = selected.reduce((minD, sel) => Math.min(minD, dist(cand, sel)), Infinity);
            if (minDistToSelected > bestMinDist) {
                bestMinDist = minDistToSelected;
                bestCandidate = cand;
            }
        }

        if (!bestCandidate) break;
        selected.push(bestCandidate);
    }

    // Get distinct targets with centers
    const targets = elements.map(el => {
        const r = el.getBoundingClientRect();
        return {target: el, center: {x: r.left + r.width / 2, y: r.top + r.height / 2}};
    });

    // Use the improved assignment function (greedy + swap)
    const assigned = assignCandidatesToTargets(selected, targets);

    // Place labels
    assigned.forEach(({candidate, target}) => {
        console.log(target.target.getAttribute('data-cyberlabel'), candidate.labelText);
        placeLabelInsideTarget(target.target, candidate.x, candidate.y);
    });
}


function assignCandidatesToTargets(candidates, targets) {
    const usedTargets = new Set();
    const assignments = [];

    // Greedy initial assignment (closest available target per candidate)
    candidates.forEach(cand => {
        let bestTarget = null;
        let bestDist = Infinity;
        for (const t of targets) {
            if (usedTargets.has(t.target)) continue;
            const d = dist(cand, t.center);
            if (d < bestDist) {
                bestDist = d;
                bestTarget = t;
            }
        }
        if (bestTarget) {
            usedTargets.add(bestTarget.target);
            assignments.push({candidate: cand, target: bestTarget});
        }
    });

    let improved = true;
    let maxRounds = 20;

    while (improved && maxRounds-- > 0) {
        improved = false;

        outer: for (let i = 0; i < assignments.length; i++) {
            for (let j = i + 1; j < assignments.length; j++) {
                const a = assignments[i];
                const b = assignments[j];

                const currentDist = dist(a.candidate, a.target.center) + dist(b.candidate, b.target.center);
                const swappedDist = dist(a.candidate, b.target.center) + dist(b.candidate, a.target.center);

                if (swappedDist < currentDist) {
                    console.log(`Swap targets: ${a.target.target.id} <-> ${b.target.target.id}, improvement: ${(currentDist - swappedDist).toFixed(2)}`);
                    [assignments[i].target, assignments[j].target] = [assignments[j].target, assignments[i].target];
                    improved = true;
                    break outer;
                }
            }
        }
    }


    return assignments;
}

function dist(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
}

function placeLabelInsideTarget(target, absX, absY) {
    const text = target.getAttribute('data-cyberlabel');
    const targetRect = target.getBoundingClientRect();

    const wrapper = document.createElement('div');
    wrapper.className = 'cyberlabel-wrapper';
    wrapper.style.position = 'absolute';
    wrapper.style.left = '0';
    wrapper.style.top = '0';
    wrapper.style.zIndex = '3';

    const label = document.createElement('div');
    label.className = 'cyberlabel-label';
    label.textContent = text;
    label.style.position = 'absolute';
    label.style.left = `${absX - targetRect.left}px`;
    label.style.top = `${absY - targetRect.top}px`;

    wrapper.appendChild(label);

    const svg = createLabelLine(target, label, absX, absY);
    wrapper.appendChild(svg);

    target.appendChild(wrapper);
}

function removeOldLabels() {
    document.querySelectorAll('.cyberlabel-wrapper').forEach(el => el.remove());
}

function createLabelLine(target, label, absX, absY) {
    const targetRect = target.getBoundingClientRect();
    const labelW = label.offsetWidth;
    const labelH = label.offsetHeight;

    const centerX = targetRect.width / 2;
    const centerY = targetRect.height / 2;

    // relative label coords inside target
    const relX = absX - targetRect.left;
    const relY = absY - targetRect.top;

    const useTop = relY + labelH / 2 < centerY;

    const lineY = useTop ? relY + labelH : relY; // bottom or top of label

    const barX1 = relX;
    const barX2 = relX + labelW;

    // Choose closest bar end to centerX
    const distStart = Math.abs(centerX - barX1);
    const distEnd = Math.abs(centerX - barX2);
    const startX = distStart < distEnd ? barX1 : barX2;

    const svgWidth = Math.max(centerX, barX2) - Math.min(centerX, barX1);
    const svgHeight = Math.max(centerY, lineY) - Math.min(centerY, lineY);

    const minX = Math.min(centerX, barX1);
    const minY = Math.min(centerY, lineY);

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('cyberlabel-svg');
    svg.setAttribute('width', svgWidth);
    svg.setAttribute('height', svgHeight);
    Object.assign(svg.style, {
        position: 'absolute',
        left: `${minX}px`,
        top: `${minY}px`,
        pointerEvents: 'none',
        zIndex: '1'
    });

    const bar = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    bar.setAttribute('x1', barX1 - minX);
    bar.setAttribute('y1', lineY - minY);
    bar.setAttribute('x2', barX2 - minX);
    bar.setAttribute('y2', lineY - minY);
    bar.setAttribute('stroke-width', '2');
    bar.setAttribute('stroke', 'currentColor');

    const connector = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    connector.setAttribute('x1', startX - minX);
    connector.setAttribute('y1', lineY - minY);
    connector.setAttribute('x2', centerX - minX);
    connector.setAttribute('y2', centerY - minY);
    connector.setAttribute('stroke-width', '2');
    connector.setAttribute('stroke', 'currentColor');

    svg.appendChild(bar);
    svg.appendChild(connector);

    return svg;
}

window.addEventListener('DOMContentLoaded', () => {
    let settleTimer = null;
    window.addEventListener('resize', renderCyberlabels);
    document.body.addEventListener('htmx:afterSettle', () => {
        clearTimeout(settleTimer);
        settleTimer = setTimeout(() => {
            renderCyberlabels();
        }, 500);
    });

    renderCyberlabels();
});
