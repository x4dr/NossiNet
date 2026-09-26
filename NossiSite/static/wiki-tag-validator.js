(function () {
    if (document.getElementById('wiki-tag-validator-init')) return
    document.documentElement.dataset.wikiTagValidator = 'loading'

    const contextEl = document.getElementById('context_element')
    const pageName = contextEl ? contextEl.textContent.trim() : ''

    function getCsrf() {
        const m = document.querySelector('meta[name="csrf-token"]')
        return m ? m.content : ''
    }

    // Number of /tag-validate requests currently in flight. Exposed via the
    // data-wiki-tag-validator attribute so callers can wait for validation to
    // settle instead of guessing with a timeout: every settled request
    // re-dispatches a transaction in the editor to force re-decoration, and
    // doing that while the user is typing moves the caret out from under them.
    let inFlight = 0

    function setPhase(phase) {
        document.documentElement.dataset.wikiTagValidator = phase
    }

    async function validate(el) {
        const raw = el.getAttribute('data-raw') || ''
        const tagType = el.getAttribute('data-type') || Array.from(el.classList).find(
            c => c !== 'tag-dirty' && c !== 'tag-valid' && c !== 'tag-invalid'
        ) || ''
        if (!tagType || !raw) return

        inFlight += 1
        setPhase('validating')
        try {
            const r = await fetch('/tag-validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
                body: JSON.stringify({ type: tagType, raw, context: pageName }),
            })
            const data = await r.json()
            window.__tagValidation[raw] = data.valid ? 'valid' : 'invalid'
            if (data.content) {
                window.__tagContent[raw] = data.content
            }
        } catch {
            window.__tagValidation[raw] = 'invalid'
        }
        inFlight -= 1
        if (inFlight === 0) setPhase('ready')

        // Trigger re-decoration so the plugin picks up the cached result
        document.dispatchEvent(new CustomEvent('tag-validation-update'))
    }

    function startObserver(root) {
        // Process existing dirty tags (from initial decoration)
        root.querySelectorAll('.tag-dirty').forEach(validate)
        if (inFlight === 0) setPhase('ready')

        // Watch for new tags introduced by editing
        const observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType === 1 && node.classList && node.classList.contains('tag-dirty')) {
                        validate(node)
                    }
                }
            }
        })
        observer.observe(root, { childList: true, subtree: true })
    }

    function init() {
        const pm = document.querySelector('.ProseMirror')
        if (pm) {
            startObserver(pm)
            return
        }
        // .ProseMirror is added later when the editor opens (dblclick)
        document.addEventListener('editor-prosemirror-ready', () => {
            const el = document.querySelector('.ProseMirror')
            if (el) startObserver(el)
        })
    }

    init()
})()
