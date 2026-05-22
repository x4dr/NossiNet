document.addEventListener('click', function (e) {
    const clock = e.target.closest('.clock-container');
    if (clock) {
        e.preventDefault();
        e.stopPropagation();

        const rect = clock.getBoundingClientRect();
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        const clickX = e.clientX - rect.left - centerX;
        const clickY = e.clientY - rect.top - centerY;

        let rawAngle = Math.atan2(clickY, clickX) * (180 / Math.PI) + 90;
        let angle = (rawAngle + 360) % 360;

        const active = parseInt(clock.dataset.active);
        const total = parseInt(clock.dataset.total);
        const activeAngle = (active / total) * 360;

        const delta = (angle < activeAngle) ? -1 : 1;

        const endpoint = `${clock.dataset.endpoint}/${delta}`;
        fetch(endpoint).catch(err => console.error("Clock update fetch failed:", err));
        return;
    }

    const target = e.target.closest('.gauge-box');
    if (target && target.hasAttribute('data-endpoint')) {
        const endpoint = target.getAttribute('data-endpoint');
        fetch(endpoint).catch(err => console.error("Gauge update fetch failed:", err));
    }
});

document.addEventListener('dblclick', function (e) {
    const clock = e.target.closest('.clock-container');
    if (clock) {
        e.preventDefault();
        e.stopPropagation();
    }
});
