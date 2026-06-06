function formatTime(date) {
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
}

window.addEventListener("load", function () {
    const globalStatus = document.getElementById('global-conn-status');
    if (globalStatus) globalStatus.style.display = '';
    const updateGlobalStatus = (state, title) => {
        if (!globalStatus) return;
        let color = 'var(--tertiary-color)';
        if (state === 'connected') color = 'var(--highlight-color, #00ff00)';
        if (state === 'error') color = 'var(--error-color, #ff0000)';
        if (state === 'connecting') color = 'var(--warn-color, #ffff00)';
        globalStatus.style.color = color;
        if (title) globalStatus.title = `SSE: ${title}`;
    };

    function updateLastSeen() {
        if (!globalStatus) return;
        const now = new Date();
        const currentTitle = globalStatus.title;
        if (currentTitle && !currentTitle.startsWith('Connected')) return;
        globalStatus.title = `Connected - Last Update: ${formatTime(now)}`;
    }

    updateGlobalStatus('connecting', 'Connecting...');
    const eventSource = new EventSource("/sse_updates");

    eventSource.onopen = function() {
        console.log("SSE Connection opened");
        updateGlobalStatus('connected', 'Connected');
        updateLastSeen();
    };

    eventSource.onerror = function(err) {
        console.error("SSE Connection error:", err);
        updateGlobalStatus('error', 'Disconnected/Error. Retrying...');
    };

    eventSource.onmessage = function (evt) {
        // This will only fire for events without a name (if any remain)
        handleSSEData(evt.data);
    };

    // Handle named events
    const eventTypes = ['clock', 'line', 'roll', 'chat'];
    eventTypes.forEach(type => {
        eventSource.addEventListener(type, function(evt) {
            handleSSEData(evt.data);
        });
    });

    function handleSSEData(raw_data) {
            updateLastSeen();
            if (globalStatus) {
                globalStatus.classList.remove('pulse');
                void globalStatus.offsetWidth;
                globalStatus.classList.add('pulse');
            }
            try {
                const data = JSON.parse(raw_data);
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

                if (data.type === 'roll') {
                    const resultEl = document.getElementById('lightning-result');
                    if (resultEl) {
                        resultEl.textContent = '';
                        resultEl.appendChild(document.createTextNode(`${data.labels} ==> `));
                        const strong = document.createElement('strong');
                        strong.textContent = data.result;
                        resultEl.appendChild(strong);

                        resultEl.classList.add('active');
                        resultEl.classList.add('flash');
                        setTimeout(() => resultEl.classList.remove('flash'), 500);
                    }
                }

                if (data.type === 'roll' || data.type === 'chat') {
                    if (document.getElementById('chatbox')) {
                        setTimeout(() => {
                            if (typeof window.updateRelativeTimes === 'function') window.updateRelativeTimes();
                            const chatbox = document.getElementById('chatbox');
                            if (chatbox) chatbox.scrollTop = chatbox.scrollHeight;
                        }, 100);
                    }
                }
            } catch (e) {
                console.error('Error parsing SSE JSON:', e);
            }
        }
});
