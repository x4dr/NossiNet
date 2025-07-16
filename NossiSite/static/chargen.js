document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener("htmx:beforeSwap", () => {
        document.querySelectorAll('.smoothtransition').forEach(el => {
            el.style.gridTemplateRows = '0fr';
        });

    });
    document.body.addEventListener("htmx:afterSwap", async e => {
        let savedRects = new Map();
        let current_element_order = [];
        let items = [];
        document.querySelectorAll('.smoothtransition').forEach(el => {
            el.style.gridTemplateRows = '1fr';
        });

        function waitForTransitions(elements) {
            return Promise.all(elements.map(el => {
                return new Promise(resolve => {
                    const computed = getComputedStyle(el);
                    const durations = computed.transitionDuration.split(',').map(s => parseFloat(s.trim()) || 0);
                    const delays = computed.transitionDelay.split(',').map(s => parseFloat(s.trim()) || 0);
                    const maxDuration = Math.max(...durations);
                    const maxDelay = Math.max(...delays);
                    const totalTime = (maxDuration + maxDelay) * 1000; // ms

                    if (totalTime === 0) {
                        resolve();
                        return;
                    }

                    let resolved = false;

                    const onEnd = (e) => {
                        if (e.target !== el) return; // ignore events from child elements
                        if (resolved) return;
                        resolved = true;
                        el.removeEventListener('transitionend', onEnd);
                        clearTimeout(timer);
                        resolve();
                    };

                    el.addEventListener('transitionend', onEnd);

                    // Fallback: resolve after expected max transition time + small buffer
                    const timer = setTimeout(() => {
                        if (resolved) return;
                        resolved = true;
                        el.removeEventListener('transitionend', onEnd);
                        resolve();
                    }, totalTime + 50);
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

            async function savestate() {
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
            }


            container.addEventListener('dragend', async () => {
                if (!draggedItem) return;
                draggedItem.classList.remove('dragging');
                if (!current_element_order.length) {
                    draggedItem = null;
                    return;
                }
                await savestate();

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
            document.getElementById("shuffle-button").addEventListener("click", async () => {

                const container = document.querySelector('.grid-container3');
                const items = Array.from(container.querySelectorAll('.draggable-item'));

                const shuffled = [...items];
                for (let i = shuffled.length - 1; i > 0; i--) {
                    const j = Math.floor(Math.random() * (i + 1));
                    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
                }
                animateVisualReorder(container, shuffled);

                await savestate();

            });
            const bars = [...document.querySelectorAll('.value .bar')];
            const points = bars.map(bar => parseFloat(bar.parentElement.textContent.trim()));
            const max = Math.max(...points);

            bars.forEach((bar, i) => {
                const scale = points[i] / max;
                bar.style.setProperty('--bar-scale', scale);
            });
            const form = document.getElementById('order-submit-button').form;
            form.addEventListener('submit', () => {
                const hidden = form.querySelector('input[name="order"]');
                hidden.value = current_element_order.map(el => el.textContent.trim()).join(',');
            });


        }
        const optionscache = {}; // global cache

        async function getOptions(heading, system = 'context') {
            if (!optionscache[heading]) {
                const res = await fetch(`/skills/${system}/${heading}`);

                const data = await res.json();
                optionscache[heading] = {
                    keys: Object.keys(data),
                    descriptions: data
                };
            }
            return optionscache[heading];
        }

        async function createFieldRow(index, heading, grid) {
            // Create input cell
            const inputCell = document.createElement('div');
            inputCell.className = 'input-cell';

            const input = document.createElement('input');
            input.type = 'text';
            input.name = 'skill';

            input.className = 'textinput skill-input';
            input.addEventListener('focus', updateDesc);
            input.addEventListener("change", updateDesc)
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

        async function ensureTrailingRowPerGrid() {
            const grids = new Set();
            document.querySelectorAll('.skill-input').forEach(input => {
                const parentGrid = input.closest('.grid-container2');
                if (parentGrid) grids.add(parentGrid);
            });

            for (const grid of grids) {
                let inputs = [...grid.querySelectorAll('.skill-input')];

                // Remove empty inputs except keep at least 3 rows
                for (let i = inputs.length - 1; i >= 0; i--) {
                    const input = inputs[i];
                    if (input.value.trim() === '') {
                        // If we have more than 3 rows, remove this empty row
                        if (inputs.length > 3) {
                            const cell = input.closest('.input-cell');
                            if (!cell) alert('No input-cell found for input');

                            const numCell = cell.nextElementSibling;
                            cell.remove();
                            if (input._autocompleteList) {
                                removeAutocompleteList(input._autocompleteList);
                                input._autocompleteList = null;
                            }
                            if (!numCell || !numCell.classList.contains('num-input')) {
                                alert('Expected num-input sibling not found after input-cell removal');
                            } else {
                                numCell.remove();
                            }
                            inputs.splice(i, 1); // update inputs array
                        }
                    }
                }

                inputs = [...grid.querySelectorAll('.skill-input')];
                while (inputs.length < 3) {
                    await createFieldRow(inputs.length, grid.dataset.heading, grid);
                    inputs = [...grid.querySelectorAll('.skill-input')];
                }

                // Ensure exactly 1 empty row at the end
                const last = inputs[inputs.length - 1];
                if (last.value.trim() !== '') {
                    await createFieldRow(inputs.length, grid.dataset.heading, grid);
                }
            }
            await setupSkillInputs()
        }

        document.addEventListener('change', async e => {
            if (e.target.classList.contains('skill-input')) {
                await ensureTrailingRowPerGrid();
            }
        });

        ensureTrailingRowPerGrid().then();

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
                newValue = index;
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

        balanceGrid('.grid-container-x');

        function validateDuplicates(input) {
            const form = input.form;
            if (!form) return;

            const inputs = [...form.querySelectorAll('.skill-input')]
            const values = inputs.map(i => i.value.trim().toLowerCase());
            const counts = values.reduce((acc, v) => {
                if (!v) return acc;
                acc[v] = (acc[v] || 0) + 1;
                return acc;
            }, {});

            inputs.forEach(i => {
                const val = i.value.trim().toLowerCase();
                if (val && counts[val] > 1) {
                    i.classList.add('error');
                } else {
                    i.classList.remove('error');
                }
            });
        }

        async function setupSkillInputs() {
            const inputs = [...document.querySelectorAll('.skill-input')];
            for (const input of inputs) {
                if (!input._listenersAdded) {
                    input.addEventListener('focus', async e => {
                        await updateDesc(e);
                    });
                    input.addEventListener('change', async e => {
                        await updateDesc(e);
                        validateDuplicates(input);
                    });
                    const grid = input.closest('.grid-container2');


                    if (!grid._used) grid._used = [];
                    grid._used.length = 0;
                    grid._used.push(
                        ...[...grid.querySelectorAll('.skill-input')]
                            .map(inp => inp.value)
                            .filter(v => v)
                    );

                    const heading = grid.dataset.heading;
                    const options = await getOptions(heading);
                    autocomplete(input, options.keys, grid._used);
                    input._listenersAdded = true;
                }
            }
        }

        async function updateDesc(event) {
            const input = event.target;
            const val = input.value;
            const grid = input.closest('.grid-container2') || input.closest('.grid-container-2');
            const heading = grid.dataset.heading?.toLowerCase();
            if (!val || !heading) return;
            const used = grid._used;
            used.length = 0;
            used.push(
                ...[...grid.querySelectorAll('.skill-input')]
                    .map(inp => inp.value)
                    .filter(v => v)
            );
            const option = await getOptions(heading);
            const desc = option.descriptions[val];
            const target = document.querySelector('#explanation');
            target.style.transition = 'opacity 0.3s ease';
            target.style.opacity = 0;
            setTimeout(() => {
                target.innerHTML = `<a href="/wiki/${heading}skills#${val}"><h3>${val}</h3></a>${desc || '<div>No Description Available!</div>'}`;
                target.style.opacity = 1;
            }, 500);
        }

        for (const inp of document.querySelectorAll('.detail-name')) {
            const grid = inp.closest('.grid-container-2');
            if (!grid._used) grid._used = [];
            const options = await getOptions("detail");
            autocomplete(inp, options.keys, grid._used);
            inp.addEventListener("change", updateDesc)
        }

    });


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
