function autocomplete(inp, arr, exclude = []) {
    attachAutocompleteListeners(inp, arr, exclude)
    inp._currentfocus = 0;


    /*execute a function presses a key on the keyboard:*/
    inp.addEventListener("keydown", function (e) {

        if (e.keyCode === 40) {
            /*If the arrow DOWN key is pressed,
            increase the currentFocus variable:*/
            inp._currentfocus++;
        } else if (e.keyCode === 38) { //up
            /*If the arrow UP key is pressed,
            decrease the currentFocus variable:*/
            inp._currentfocus--;

        }
        const list = inp._autocompleteList;
        if (inp._currentfocus >= list.children.length || isNaN(inp._currentfocus)) inp._currentfocus = 0;
        if (inp._currentfocus < 0) inp._currentfocus = (list.children.length - 1);
        x = list.children.item(inp._currentfocus)
        const last = makeActive(x);
        if (e.keyCode === 13) {
            e.preventDefault();
            last.click();
            removeAutocompleteList(inp._autocompleteList);
            inp._autocompleteList = null;
        }

    });


}

let lastactive = null;

function makeActive(x) {
    if (!x) return false;
    let last = lastactive
    if (lastactive) lastactive?.classList?.remove("autocomplete-active");
    lastactive = x
    x.classList.add("autocomplete-active");
    return last;

}

function buildAutocompleteList(arr, inp) {
    document.querySelectorAll('.autocomplete-items').forEach(removeAutocompleteList);
    const container = document.createElement("div");
    container.className = "autocomplete-items";
    for (const val of arr) {
        const item = document.createElement("div");
        item.onmouseover = () => {
            makeActive(item)
        };
        item.onclick = () => assignItem(item, inp, val);
        item.textContent = val;
        container.appendChild(item);
    }
    return container;
}

function positionAutocompleteList(inp, list) {
    const rect = inp.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const maxBottom = vh * 0.9;
    const inputBottom = rect.bottom + window.scrollY;
    const maxHeightBelow = maxBottom - inputBottom;

    // Calculate input center for animation origin
    const inputCenterX = rect.left + rect.width / 2 + window.scrollX;
    const inputCenterY = rect.top + rect.height / 2 + window.scrollY;

    // Ensure the list doesn't go off-screen horizontally
    const listWidth = rect.width;
    const maxLeft = vw - listWidth;
    const rightPos = Math.min(rect.right + window.scrollX, maxLeft);
    const leftPos = Math.min(rect.left + window.scrollX, maxLeft);

    // Position the list
    if (rect.bottom > vh * 0.4) {
        list.style.bottom = `${maxHeightBelow}px`;
        list.style.top = 'auto';
        list.style.left = `${rightPos}px`;
        const availableHeightAbove = rect.top + window.scrollY;
        list.style.maxHeight = `${Math.min(vh * 0.5, availableHeightAbove)}px`;
        list.style.overflowY = 'auto';
    } else {
        list.style.top = `${inputBottom}px`;
        list.style.bottom = 'auto';
        list.style.left = `${leftPos}px`;
        const availableHeightBelow = vh - rect.bottom;
        list.style.maxHeight = `${Math.min(vh * 0.5, availableHeightBelow)}px`;
        list.style.overflowY = 'auto';
    }

    list.style.width = `${rect.width}px`;
    list.style.position = 'absolute';
    list.style.zIndex = 3;
    // Animate list items
    const items = list.querySelectorAll('div');
    items.forEach((item, index) => {
        // Get item center relative to final position
        const itemRect = item.getBoundingClientRect();
        const itemCenterX = itemRect.left + itemRect.width / 2 + window.scrollX;
        const itemCenterY = itemRect.top + itemRect.height / 2 + window.scrollY;

        // Calculate translation to align item center with input center
        const translateX = inputCenterX - itemCenterX;
        const translateY = inputCenterY - itemCenterY;

        // Set initial state
        item.style.transform = `translate(${translateX}px, ${translateY}px)`;
        item.style.opacity = '0';
        const transition = item.style.transition;
        item.style.transition = 'none'; // Prevent initial transition

        // Trigger animation after a slight delay to ensure positioning
        setTimeout(() => {
            item.style.transform = 'translate(0, 0)';
            item.style.transition = transition;
            item.style.removeProperty('opacity');
        }, index * 10); // Stagger animations slightly for visual effect
    });
}

function removeAutocompleteList(list) {
    if (!list) return;
    list.zIndex = 1
    list.style.transition = 'opacity 0.5s ease-out';
    list.style.opacity = '0';
    setTimeout(() => {
        if (list.parentNode) {
            list.remove();
        }
    }, 500); // Match the 0.5s fade-out duration
}

function assignItem(item, inp, val) {

    const rect = item.getBoundingClientRect();
    const inputRect = inp.getBoundingClientRect();

    const style = getComputedStyle(inp);
    const paddingLeft = parseFloat(style.paddingLeft);
    const paddingTop = parseFloat(style.paddingTop);

    const clone = item.cloneNode(true);
    clone.style.position = 'fixed';
    clone.style.left = rect.left + 'px';
    clone.style.top = rect.top + 'px';

    // Copy font styles only
    clone.style.font = style.font;

    clone.style.transition = 'all 0.1s ease-in';
    clone.style.background = 'var(--primary-color)';
    clone.style.color = 'var(--background-color)';
    clone.style.opacity = '1';
    document.body.appendChild(clone);

    const translateX = inputRect.left - rect.left + paddingLeft;
    const translateY = inputRect.top - rect.top + paddingTop;

    setTimeout(() => {
        clone.style.transform = `translate(${translateX}px, ${translateY}px)`;
        clone.style.opacity = '1';
        clone.style.color = 'var(--primary-color)';
        clone.style.background = 'var(--background-color)';
    }, 80);

    const cleanup = () => {
        if (clone.parentElement) {
            clone.remove();
            inp.value = val;
            inp.dispatchEvent(new Event('change', {bubbles: true}));
        }
    };

    setTimeout(cleanup, 1000);
    clone.addEventListener('transitionend', cleanup);
}


function attachAutocompleteListeners(inp, arr, exclude) {
    inp.addEventListener('focus', () => {
        if (!inp._autocompleteList) {
            inp._autocompleteList = buildAutocompleteList(arr.filter(x => !exclude.includes(x)), inp);
            makeActive(inp._autocompleteList.children.item(0));
            inp._currentfocus = 0;
            document.body.appendChild(inp._autocompleteList);
            positionAutocompleteList(inp, inp._autocompleteList);
        }
    });

    inp.addEventListener('blur', () => {
        if (inp._autocompleteList) {
            removeAutocompleteList(inp._autocompleteList);
            inp._autocompleteList = null;
        }
    });
}
