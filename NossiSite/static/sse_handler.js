window.addEventListener("load", function () {
    // Delay initialization to ensure the DOM has settled
    setTimeout(function () {
        const eventSource = new EventSource("/sse_updates");

        eventSource.onmessage = function (evt) {
            try {
                const data = JSON.parse(evt.data);
                const targetEl = document.getElementById(data.target);
                if (targetEl) {
                    if (data.type === 'clock') {
                        // Update clock visual via custom properties
                        targetEl.style.setProperty('--clock-active', data.current);
                        targetEl.style.setProperty('--clock-total', data.total);
                        targetEl.dataset.active = data.current;
                        targetEl.dataset.total = data.total;
                    } else if (data.type === 'line') {
                        // Existing line logic
                        const boxes = targetEl.querySelectorAll('.gauge-box');
                        boxes.forEach((box, i) => {
                            box.className = (i < data.current) ? 'gauge-box filled' : 'gauge-box empty';
                        });
                    }
                }
            } catch (e) {
                console.error('Error parsing SSE JSON:', e);
            }
        };

        document.addEventListener('click', function (e) {
            const clock = e.target.closest('.clock-container');
            if (clock) {
                // Prevent bubbling to parents (like click triggers for modals)
                e.preventDefault();
                e.stopPropagation();

                const rect = clock.getBoundingClientRect();
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const clickX = e.clientX - rect.left - centerX;
                const clickY = e.clientY - rect.top - centerY;

                // Polar coordinate angle (0 is at top)
                let rawAngle = Math.atan2(clickY, clickX) * (180 / Math.PI) + 90;
                // Normalize angle to [0, 360)
                let angle = (rawAngle + 360) % 360;

                // Active angle
                const active = parseInt(clock.dataset.active);
                const total = parseInt(clock.dataset.total);
                const activeAngle = (active / total) * 360;

                // Logic: click in active sector = decrease (-1)
                const delta = (angle < activeAngle) ? -1 : 1;

                const endpoint = `${clock.dataset.endpoint}/${delta}`;
                fetch(endpoint).catch(err => console.error("Clock update fetch failed:", err));
                return;
            }

            // Existing gauge/other logic
            const target = e.target.closest('.gauge-box');
            if (target && target.hasAttribute('data-endpoint')) {
                const endpoint = target.getAttribute('data-endpoint');
                fetch(endpoint).catch(err => console.error("Gauge update fetch failed:", err));
            }
        });

        document.addEventListener('dblclick', function (e) {
            const clock = e.target.closest('.clock-container');
            if (clock) {
                // Stop bubbling on double click to prevent modal opening
                e.preventDefault();
                e.stopPropagation();
            }
        });
    }, 1000); // 1-second delay
});
