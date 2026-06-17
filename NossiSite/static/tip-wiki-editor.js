let editor = null

async function openWikiEditor(wikiName) {
    try {
        const csrf = document.querySelector('meta[name="csrf-token"]').content

        const reply = await fetch('/live_edit', {
            method: 'POST',
            body: JSON.stringify({context: wikiName, type: 'tiptap', path: [], percentage: ''}),
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
        }).then(r => {
            if (!r.ok) throw new Error(`fetch failed: ${r.status}`)
            return r.json()
        })

        if (!reply.data) return
        const original = reply.data

        const wrapper = document.createElement('div')
        wrapper.className = 'tip-overlay'
        wrapper.innerHTML = `
            <div class="tip-panel">
                <div class="tip-toolbar" id="tip-toolbar">
                    <button data-tip-cmd="bold" title="Bold"><b>B</b></button>
                    <button data-tip-cmd="italic" title="Italic"><i>I</i></button>
                    <button data-tip-cmd="strike" title="Strikethrough"><s>S</s></button>
                    <button data-tip-cmd="code" title="Inline code">&lt;/&gt;</button>
                    <span class="tip-sep"></span>
                    <button data-tip-cmd="h1" title="Heading 1">H1</button>
                    <button data-tip-cmd="h2" title="Heading 2">H2</button>
                    <button data-tip-cmd="h3" title="Heading 3">H3</button>
                    <span class="tip-sep"></span>
                    <button data-tip-cmd="bulletList" title="Bullet list">ul</button>
                    <button data-tip-cmd="orderedList" title="Ordered list">ol</button>
                    <span class="tip-sep"></span>
                    <button data-tip-cmd="blockquote" title="Blockquote">"</button>
                    <button data-tip-cmd="codeBlock" title="Code block">{ }</button>
                    <button data-tip-cmd="horizontalRule" title="Horizontal rule">hr</button>
                </div>
                <div id="tip-editor"></div>
                <div class="tip-actions">
                    <button class="tip-btn tip-cancel" id="tip-close">Cancel</button>
                    <button class="tip-btn tip-save" id="tip-save">Save</button>
                </div>
            </div>
        `
        document.body.appendChild(wrapper)

        const { Editor, StarterKit, Markdown } = await import('/static/lib/tiptap/tip-edit.js')

        editor = new Editor({
            element: document.querySelector('#tip-editor'),
            extensions: [
                StarterKit.configure({history: {depth: 100}}),
                Markdown.configure({indentation: {style: 'space', size: 2}}),
            ],
            content: original,
            contentType: 'markdown',
            autofocus: 'end',
        })

        const btns = wrapper.querySelectorAll('[data-tip-cmd]')
        function updateActive() {
            btns.forEach(b => {
                const cmd = b.dataset.tipCmd
                let active = false
                switch (cmd) {
                    case 'bold': active = editor.isActive('bold'); break
                    case 'italic': active = editor.isActive('italic'); break
                    case 'strike': active = editor.isActive('strike'); break
                    case 'code': active = editor.isActive('code'); break
                    case 'h1': active = editor.isActive('heading', {level: 1}); break
                    case 'h2': active = editor.isActive('heading', {level: 2}); break
                    case 'h3': active = editor.isActive('heading', {level: 3}); break
                    case 'bulletList': active = editor.isActive('bulletList'); break
                    case 'orderedList': active = editor.isActive('orderedList'); break
                    case 'blockquote': active = editor.isActive('blockquote'); break
                    case 'codeBlock': active = editor.isActive('codeBlock'); break
                }
                b.classList.toggle('tip-active', active)
            })
        }

        const cmdMap = {
            bold: 'toggleBold', italic: 'toggleItalic', strike: 'toggleStrike',
            code: 'toggleCode', h1: ['toggleHeading', {level: 1}],
            h2: ['toggleHeading', {level: 2}], h3: ['toggleHeading', {level: 3}],
            bulletList: 'toggleBulletList', orderedList: 'toggleOrderedList',
            blockquote: 'toggleBlockquote', codeBlock: 'toggleCodeBlock',
            horizontalRule: 'setHorizontalRule',
        }

        btns.forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.tipCmd
                const spec = cmdMap[cmd]
                if (!spec) return
                if (typeof spec === 'string') {
                    editor.chain().focus()[spec]().run()
                } else {
                    const [method, args] = spec
                    editor.chain().focus()[method](args).run()
                }
                updateActive()
            })
        })

        editor.on('selectionUpdate', updateActive)

        wrapper.querySelector('#tip-close').addEventListener('click', closeEditor)

        wrapper.querySelector('#tip-save').addEventListener('click', async () => {
            try {
                const md = editor.getMarkdown()
                const fd = new FormData()
                fd.append('wiki', wikiName)
                fd.append('type', 'tiptap')
                fd.append('body', md)
                fd.append('csrf_token', csrf)
                await fetch('/live_edit', {method: 'POST', body: new URLSearchParams(fd)})
                closeEditor()
                location.reload()
            } catch (e) {
                console.error('save error:', e)
            }
        })

        wrapper.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeEditor()
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                wrapper.querySelector('#tip-save').click()
            }
        })

        editor.commands.focus()
    } catch (e) {
        console.error('tip-wiki-editor error:', e)
    }
}

function closeEditor() {
    if (editor) { editor.destroy(); editor = null }
    const el = document.querySelector('.tip-overlay')
    if (el) el.remove()
}

document.addEventListener('DOMContentLoaded', () => {
    const body = document.getElementById('wikibody')
    const ctx = document.getElementById('context_element')
    if (!body || !ctx) return
    const name = ctx.textContent.trim()
    ctx.remove()
    body.addEventListener('dblclick', () => openWikiEditor(name))
})
