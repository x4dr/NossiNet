document.addEventListener("DOMContentLoaded", () => {
    let isProcessing = false;

    document.body.addEventListener('htmx:beforeRequest', () => {
        isProcessing = true
    });
    document.body.addEventListener('htmx:afterRequest', () => {
        isProcessing = false
    });
    document.body.addEventListener("htmx:afterSwap", () => {
        let savedRects = new Map();
        let current_element_order = [];
        let items = [];

        function updateDesc(event) {
            const input = event.target;
            const val = input.value;
            const heading = input.closest('.grid-container2')?.dataset.heading?.toLowerCase();
            if (!val || !heading) return;

            const datalist = document.getElementById(input.getAttribute('list'));
            const option = Array.from(datalist.options)
                .find(o => o.value.toLowerCase() === val.toLowerCase());
            const desc = option?.dataset.desc;

            const target = document.querySelector('#explanation');
            target.style.transition = 'opacity 0.2s ease';
            target.style.opacity = 0;
            setTimeout(() => {
                target.innerHTML = `<h3>${val}</h3>${desc || 'No Description Available!'}`;
                target.style.opacity = 1;
            }, 300);
        }

        function waitForTransitions(elements) {
            return Promise.all(elements.map(el => {
                return new Promise(resolve => {
                    const onEnd = () => {
                        el.removeEventListener('transitionend', onEnd);
                        resolve();
                    };

                    // If there's no active transition, resolve immediately
                    const computed = getComputedStyle(el);
                    const duration = parseFloat(computed.transitionDuration) || 0;
                    if (duration === 0) {
                        resolve();
                    } else {
                        el.addEventListener('transitionend', onEnd);
                    }
                });
            }));
        }

        function animateVisualReorder(container, newOrder) {
            current_element_order = newOrder
            newOrder.forEach((el, i) => {
                const targetRect = savedRects.get(i);
                if (!targetRect) return;

                const original_rect = savedRects.get(items.indexOf(el))
                const dx = targetRect.left - original_rect.left;
                const dy = targetRect.top - original_rect.top;
                el.style.transform = `translate(${dx}px, ${dy}px)`;
            });
        }

        const container = document.querySelector('.grid-container3');
        if (container) {
            let draggedItem = null;
            items = Array.from(container.querySelectorAll('.draggable-item'));
            current_element_order = items;
            items.forEach((el, i) => {
                savedRects.set(i, el.getBoundingClientRect());
            });

            container.addEventListener('dragstart', e => {
                if (!e.target.classList.contains('draggable-item')) return;
                draggedItem = e.target;
                draggedItem.classList.add('dragging');
            });


            container.addEventListener('dragend', async e => {
                if (!draggedItem) return;
                draggedItem.classList.remove('dragging');

                if (!current_element_order.length) {
                    draggedItem = null;
                    return;
                }
                await waitForTransitions(current_element_order);
                // Clean up styles
                current_element_order.forEach(el => {
                    el.style.transform = '';
                });

                // Get all children
                const allChildren = Array.from(container.children);

                // Find indices of old draggables in full container list
                const insertionPoints = allChildren.reduce((acc, el, i) => {
                    if (el.classList.contains('draggable-item')) acc.push(i);
                    return acc;
                }, []);

                // Insert each element before the next non-draggable or end
                current_element_order.forEach((el, i) => {
                    const index = insertionPoints[i];
                    const refNode = allChildren[index + 1] || null;
                    container.insertBefore(el, refNode);
                });

                draggedItem = null;
                items = Array.from(container.querySelectorAll('.draggable-item'));

                items.forEach((el, i) => {
                    savedRects.set(i, el.getBoundingClientRect());
                });
            });


            container.addEventListener('dragover', e => {
                e.preventDefault();
                if (!draggedItem) return;

                const order = Array.from(container.querySelectorAll('.draggable-item'));

                const containerRect = container.getBoundingClientRect();
                const zones = order.length + 1;
                const zoneHeight = containerRect.height / zones;
                const y = e.clientY - containerRect.top;

                let newIndex = Math.floor((y - (zoneHeight / 2)) / zoneHeight);
                if (newIndex > order.length) newIndex = order.length;
                if (newIndex < 0) newIndex = 0;
                const draggedIndex = items.indexOf(draggedItem);
                const newOrder = items.slice();
                newOrder.splice(draggedIndex, 1);
                newOrder.splice(newIndex, 0, draggedItem);

                animateVisualReorder(container, newOrder);
            });
            document.getElementById("shuffle-button").addEventListener("click", () => {

                const container = document.querySelector('.grid-container3');
                const items = Array.from(container.querySelectorAll('.draggable-item'));

                const shuffled = [...items];
                for (let i = shuffled.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
                }
                animateVisualReorder(container, shuffled);
            });
            const bars = [...document.querySelectorAll('.value .bar')];
            const points = bars.map(bar => parseFloat(bar.parentElement.textContent.trim()));
            const max = Math.max(...points);

            bars.forEach((bar, i) => {
                const scale = points[i] / max;
                bar.style.setProperty('--bar-scale', scale);
            });
            const form = document.getElementById('order-submit-button').form;
            form.addEventListener('submit', e => {
                const hidden = form.querySelector('input[name="order"]');
                hidden.value = current_element_order.map(el => el.textContent.trim()).join(',');
            });

            const grid = document.getElementById('criteria-grid');
        }

        function createFieldRow(index, heading, grid) {
            // Create input cell
            const inputCell = document.createElement('div');
            inputCell.className = 'input-cell';

            const input = document.createElement('input');
            input.type = 'text';
            input.name = 'skill';
            input.setAttribute('list', `${heading}_skills`);
            input.className = 'textinput skill-input';
            input.addEventListener('focus', updateDesc);
            input.addEventListener('input', updateDesc);

            inputCell.appendChild(input);


            const numInput = document.createElement('div');
            numInput.className = 'num-input';
            numInput.onclick = numinput_handle;

            const maxButtons = 3; // adjust if needed
            for (let i = 0; i < maxButtons; i++) {
                const btn = document.createElement('button');
                btn.type = 'button';
                numInput.appendChild(btn);
            }

            // Hidden input to hold selected value
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'value';
            hiddenInput.value = '0';
            numInput.appendChild(hiddenInput);

            // Append both to grid container
            grid.appendChild(inputCell);
            grid.appendChild(numInput);
        }

        function ensureTrailingRowPerGrid() {
            const grids = new Set();
            document.querySelectorAll('.skill-input').forEach(input => {
                const parentGrid = input.closest('.grid-container2');
                if (parentGrid) grids.add(parentGrid);
            });

            grids.forEach(grid => {
                const inputs = grid.querySelectorAll('.skill-input');
                const last = inputs[inputs.length - 1];
                if (last && last.value.trim() !== '') {
                    createFieldRow(inputs.length, grid.dataset.heading, grid);
                }
            });
        }

        document.addEventListener('change', e => {
            if (e.target.classList.contains('skill-input')) {
                ensureTrailingRowPerGrid();
            }
        });

        ensureTrailingRowPerGrid(); // in case last one is already filled

        function recalculate_points(formEl) {
            const total = [...formEl.querySelectorAll('.num-input')].reduce((sum, input) => {
                const val = parseInt(input.querySelector('input[type="hidden"]')?.value || '0', 10);
                return sum + val;
            }, 0);
            const display = formEl.querySelector('.showpoints');
            if (display) updateShowpoints(display, total);
        }

        function numinput_handle(e) {
            if (e.target.tagName !== 'BUTTON') return;

            const container = e.currentTarget;
            const btns = [...container.children].filter(el => el.tagName === 'BUTTON');
            const index = btns.indexOf(e.target);

            let newValue;
            if (e.target.classList.contains('active')) {
                newValue = 0;
            } else {
                newValue = index + 1;
            }
            const input = container.querySelector('input[type="hidden"]');
            input.value = newValue;
            input.dispatchEvent(new Event('change', {bubbles: true}));

            btns.forEach((btn, i) => btn.classList.toggle('active', i < newValue));
            const form = container.closest('.skill-form');
            if (form) recalculate_points(form);
        }

        document.querySelectorAll('.skill-form').forEach(form => recalculate_points(form));

        document.querySelectorAll('.num-input').forEach(el => {
            el.onclick = numinput_handle;
        });

        let lastSentAll = {data: null};

        function sendAllSkillForms(extraParams = {}) {
            let allCategories = {};
            document.querySelectorAll('.skill-form').forEach(f => {
                const heading = "category_" + f.querySelector('input[name="heading"]').value;
                const inputs = f.querySelectorAll('.skill-input');
                const result = {};

                inputs.forEach(input => {
                    const name = input.value.trim();
                    if (!name) return;
                    const valInput = input.closest('.input-cell').nextElementSibling.querySelector('input[type="hidden"]');
                    result[name] = parseInt(valInput?.value || "0");
                });

                allCategories[heading] = JSON.stringify(result);
            });

            Object.assign(allCategories, extraParams);

            const serializedAll = JSON.stringify(allCategories);
            if (lastSentAll.data === serializedAll) return;
            lastSentAll.data = serializedAll;

            allCategories.csrf_token = document.querySelector('input[name="csrf_token"]')?.value;

            htmx.ajax('POST', '/chargen', {
                values: allCategories,
                swap: extraParams.stage ? 'innerHTML' : 'none',
                target: '#question'
            });
        }

        balanceGrid('.grid-container-x');

        document.querySelectorAll('input[list]').forEach(input => {
            input.addEventListener('focus', updateDesc);
            input.addEventListener('input', updateDesc);
        });
        document.querySelectorAll('.textbtn').forEach(button => {
            button.removeEventListener('click', onTextBtnClick);
            button.addEventListener('click', onTextBtnClick);
        });
    });

    function onTextBtnClick(evt) {
        if (isProcessing) {
            evt.preventDefault();
            document.body.addEventListener('htmx:afterRequest', () => {
                htmx.trigger(evt.target, 'click');
            }, {once: true});
        }
    }

    function updateShowpoints(el, current) {
        const max = parseInt(el.dataset.max, 10);
        if (isNaN(max)) return;

        const diff = max - current;
        const pct = Math.min(Math.max(current / max, 0), 1) * 100;
        if (diff < 0) {
            el.classList.add('over100');
        } else {
            el.classList.remove('over100');
        }

        el.style.setProperty('--diff-content', `"${diff}"`);
        el.style.setProperty('--bar-pct', `${pct}%`);
    }

    function balanceGrid(selector) {
        document.querySelectorAll(selector).forEach(container => {
            const children = [...container.children];
            const gap = 16;
            const containerWidth = container.clientWidth;
            const totalChildren = children.length;

            let perRow = totalChildren;

            for (; perRow > 1; perRow--) {
                const childWidths = children
                    .slice(0, perRow)
                    .map(c => c.getBoundingClientRect().width);
                const totalWidth = childWidths.reduce((a, b) => a + b, 0) + (perRow - 1) * gap;

                if (totalWidth <= containerWidth) break;
            }

            const rows = Math.ceil(totalChildren / perRow);
            perRow = Math.ceil(totalChildren / rows);

            container.style.setProperty('--per-row', perRow);
        });
    }


    window.addEventListener('resize', () => balanceGrid('.grid-container-x'));
});
