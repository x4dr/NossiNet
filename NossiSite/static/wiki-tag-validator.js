(function () {
    if (document.getElementById('wiki-tag-validator-init')) return
    document.documentElement.dataset.wikiTagValidator = 'loading'

    const contextEl = document.getElementById('context_element')
    const pageName = contextEl ? contextEl.textContent.trim() : ''

    function getCsrf() {
        const m = document.querySelector('meta[name="csrf-token"]')
        return m ? m.content : ''
    }

    async function validate(el) {
        const raw = el.getAttribute('data-raw') || ''
        const classes = Array.from(el.classList)
        const tagType = classes.find(c => c !== 'tag-dirty' && c !== 'tag-valid' && c !== 'tag-invalid') || ''
        if (!tagType || !raw) return

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

        // Trigger re-decoration so the plugin picks up the cached result
        document.dispatchEvent(new CustomEvent('tag-validation-update'))
    }

    function startObserver(root) {
        // Process existing dirty tags (from initial decoration)
        root.querySelectorAll('.tag-dirty').forEach(validate)

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
            document.documentElement.dataset.wikiTagValidator = 'ready'
            return
        }
        // .ProseMirror is added later when the editor opens (dblclick)
        document.addEventListener('editor-prosemirror-ready', () => {
            const el = document.querySelector('.ProseMirror')
            if (el) {
                startObserver(el)
                document.documentElement.dataset.wikiTagValidator = 'ready'
            }
        })
    }

    init()
})()
