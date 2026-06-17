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
            if (data.valid) {
                el.classList.remove('tag-dirty')
                el.classList.add('tag-valid')
                if (data.content) {
                    el.setAttribute('data-tooltip-content', data.content)
                }
            } else {
                el.classList.remove('tag-dirty')
                el.classList.add('tag-invalid')
            }
        } catch {
            el.classList.remove('tag-dirty')
            el.classList.add('tag-invalid')
        }
    }

    let pending = new Set()
    let timer = null

    function schedule(el) {
        pending.add(el)
        if (!timer) {
            timer = setTimeout(() => {
                timer = null
                const batch = Array.from(pending)
                pending.clear()
                batch.forEach(validate)
            }, 200)
        }
    }

    function startObserver(root) {
        const observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType === 1) {
                        if (node.classList && node.classList.contains('tag-dirty')) {
                            schedule(node)
                        }
                        if (node.querySelectorAll) {
                            node.querySelectorAll('.tag-dirty').forEach(schedule)
                        }
                    }
                }
            }
        })
        observer.observe(root, { childList: true, subtree: true })
        return observer
    }

    function init() {
        const pm = document.querySelector('.ProseMirror')
        if (!pm) {
            document.addEventListener('DOMContentLoaded', () => {
                const el = document.querySelector('.ProseMirror')
                if (el) { startObserver(el); document.documentElement.dataset.wikiTagValidator = 'ready' }
            })
            return
        }
        startObserver(pm)
        document.documentElement.dataset.wikiTagValidator = 'ready'
    }

    init()

    let tooltipEl = null

    function showTooltip(e) {
        const el = e.target.closest('[data-tooltip-content]')
        if (!el) { hideTooltip(); return }
        const content = el.getAttribute('data-tooltip-content') || ''
        if (!content) return
        if (!tooltipEl) {
            tooltipEl = document.createElement('div')
            tooltipEl.className = 'tag-tooltip'
            document.body.appendChild(tooltipEl)
        }
        tooltipEl.textContent = content
        requestAnimationFrame(() => {
            const r = el.getBoundingClientRect()
            tooltipEl.style.left = Math.min(r.left + r.width / 2 - tooltipEl.offsetWidth / 2, window.innerWidth - tooltipEl.offsetWidth - 8) + 'px'
            tooltipEl.style.top = (r.bottom + 6) + 'px'
            tooltipEl.style.display = 'block'
        })
    }

    function hideTooltip() {
        if (tooltipEl) { tooltipEl.style.display = 'none' }
    }

    document.addEventListener('mouseover', showTooltip)
    document.addEventListener('mouseout', (e) => {
        if (!e.relatedTarget || !e.relatedTarget.closest) return
        if (!e.relatedTarget.closest('[data-tooltip-content]')) hideTooltip()
    })
})()
