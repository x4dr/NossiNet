let editor = null
let sourceMode = false

function getWikiTags() {
    const el = document.getElementById('wiki-tags-data')
    if (!el) return []
    try { return JSON.parse(el.textContent) } catch { return [] }
}

function createClockNode(pm) {
    const { Node } = pm
    return Node.create({
        name: 'clock',
        group: 'inline',
        inline: true,
        atom: true,
        addAttributes() {
            return {
                name: { default: '' },
                current: { default: 0 },
                total: { default: 1 },
                page: { default: '' },
            }
        },
        parseHTML() {
            return [{ tag: 'div.clock-container', getAttrs: (dom) => ({
                name: dom.getAttribute('data-name') || '',
                current: parseInt(dom.getAttribute('data-active') || '0'),
                total: parseInt(dom.getAttribute('data-total') || '1'),
            }) }]
        },
        renderHTML({ node }) {
            const { current, total, name } = node.attrs
            const ticks = []
            if (total > 1) {
                const step = 360 / total
                for (let i = 0; i < total; i++) {
                    ticks.push(['div', { class: 'tick', style: `transform: rotate(${i * step}deg)` }])
                }
            }
            return [
                'div',
                {
                    class: 'clock-container',
                    'data-active': String(current),
                    'data-total': String(total),
                    'data-name': name,
                    style: `--clock-active: ${current}; --clock-total: ${total};`,
                },
                ['div', { class: 'clock-ticks' }, ...ticks],
            ]
        },
        renderMarkdown(node, h2) {
            const { name, current, total } = node.attrs
            return `[clock|${name}|${current}|${total}]`
        },
        parseMarkdown(token, helpers) {
            return helpers.createNode('clock', token.attrs || {}, [])
        },
        markdownTokenizer: {
            name: 'clock',
            level: 'inline',
            start(src) { return src.indexOf('[clock|') },
            tokenize(src) {
                const m = /^\[clock\|([^|]+)\|(\d+)\|(\d+)]/.exec(src)
                if (!m) return undefined
                return {
                    type: 'clock',
                    raw: m[0],
                    text: m[0],
                    attrs: { name: m[1], current: parseInt(m[2]), total: parseInt(m[3]) },
                }
            },
        },
        addCommands() {
            return {
                insertClock: (attrs) => ({ commands }) => commands.insertContent({ type: 'clock', attrs }),
            }
        },
    })
}

function createWikiTagPlugin(tags, pm) {
    const { Extension, Plugin, Decoration, DecorationSet } = pm
    const tagPatterns = tags
        .filter(t => t.pattern && t.category !== 'internal' && t.id !== 'clock')
        .map(t => {
            const jsPattern = t.pattern.replace(/\(\?P<([^>]+)>/g, '(?<$1>')
            const flags = t.flags ? t.flags + 'g' : 'g'
            return { id: t.id, regex: new RegExp(jsPattern, flags) }
        })

    return Extension.create({
        name: 'wikiTagDecorations',
        addProseMirrorPlugins() {
            return [
                new Plugin({
                    props: {
                        decorations(state) {
                            const decos = []
                            const doc = state.doc

                            doc.descendants((node, pos) => {
                                if (node.isText) {
                                    const text = node.text
                                    for (const { id, regex } of tagPatterns) {
                                        regex.lastIndex = 0
                                        let match
                                        while ((match = regex.exec(text)) !== null) {
                                            if (match.index === regex.lastIndex) { regex.lastIndex++; continue }
                                            decos.push(
                                                Decoration.inline(pos + match.index, pos + match.index + match[0].length, {
                                                    class: `tag-dirty ${id}`,
                                                    'data-raw': match[0],
                                                })
                                            )
                                        }
                                    }
                                }

                                if (node.type.name === 'heading') {
                                    const first = node.firstChild
                                    if (first && first.isText && first.text.startsWith('!')) {
                                        decos.push(
                                            Decoration.node(pos, pos + node.nodeSize, { class: 'foldable-heading' })
                                        )
                                    }
                                }
                            })

                            return DecorationSet.create(doc, decos)
                        },
                    },
                }),
            ]
        },
    })
}

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

        const tags = getWikiTags().filter(t => t.category !== 'internal')

        const wrapper = document.createElement('div')
        wrapper.className = 'tip-overlay'

        let tagOptions = ''
        for (const t of tags) {
            tagOptions += `<option value="${t.syntax.replace(/"/g, '&quot;')}">${t.id}</option>`
        }

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
                    <span class="tip-sep"></span>
                    <label class="tip-tag-label">Wiki Tag
                        <select class="tip-tag-select" id="tip-tag-select">
                            <option value="">— insert —</option>
                            ${tagOptions}
                        </select>
                    </label>
                </div>
                <div id="tip-editor"></div>
                <textarea id="tip-source-area" class="tip-source-area" spellcheck="false"></textarea>
                <div class="tip-actions">
                    <button class="tip-btn tip-source-toggle" id="tip-source-toggle">&lt;/&gt; Source</button>
                    <button class="tip-btn tip-cancel" id="tip-close">Cancel</button>
                    <button class="tip-btn tip-save" id="tip-save">Save</button>
                </div>
            </div>
        `
        document.body.appendChild(wrapper)

        const m = await import('/static/lib/tiptap/tip-edit.js')
        const { Editor, StarterKit, Markdown, TaskList, TaskItem, Strike, Marked, Node } = m
        const wikTagsPlugin = createWikiTagPlugin(tags, m)
        const ClockNode = createClockNode(m)

        // Patch marked's del tokenizer to only match ~~, not single ~
        // (single tilde glitch g~text~g and invert i~text~i use ~ as literal text)
        const origDel = Marked.Tokenizer.prototype.del
        Marked.Tokenizer.prototype.del = function (e, ...a) {
            const m = this.rules.inline.delLDelim.exec(e)
            if (m && [...m[0]].length - 1 === 1) return undefined
            return origDel.call(this, e, ...a)
        }

        editor = new Editor({
            element: document.querySelector('#tip-editor'),
            extensions: [
                StarterKit.configure({history: {depth: 100}, strike: false}),
                Strike,
                Markdown.configure({indentation: {style: 'space', size: 2}}),
                TaskList,
                TaskItem.configure({nested: true}),
                ClockNode,
                wikTagsPlugin,
            ],
            content: original,
            contentType: 'markdown',
            autofocus: 'end',
        })

        // Don't escape ~ in text serialization — we patched marked to reject single ~
        const mgr = editor.markdown
        if (mgr && mgr.escapeMarkdownSyntax) {
            const orig = mgr.escapeMarkdownSyntax.bind(mgr)
            mgr.escapeMarkdownSyntax = function (text) {
                return text.replace(/([\\`*_\[\]])/g, '\\$1')
            }
        }

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

        const tagSelect = wrapper.querySelector('#tip-tag-select')
        tagSelect.addEventListener('change', () => {
            const val = tagSelect.value
            tagSelect.value = ''
            if (!val || !editor) return
            editor.chain().focus().insertContent(val).run()
        })

        function getContent() {
            if (sourceMode) {
                return document.getElementById('tip-source-area').value
            }
            return editor.getMarkdown()
        }

        async function toggleSource() {
            const editorEl = document.getElementById('tip-editor')
            const sourceEl = document.getElementById('tip-source-area')
            const btn = document.getElementById('tip-source-toggle')
            sourceMode = !sourceMode
            if (sourceMode) {
                sourceEl.value = editor.getMarkdown()
                editorEl.style.display = 'none'
                sourceEl.style.display = 'block'
                btn.textContent = '</> WYSIWYG'
                sourceEl.focus()
            } else {
                const md = sourceEl.value
                editor.destroy()
                editorEl.style.display = 'block'
                sourceEl.style.display = 'none'
                btn.textContent = '</> Source'
                const m2 = await import('/static/lib/tiptap/tip-edit.js')
                const { Editor: Ed, StarterKit: SK, Markdown: Md, TaskList: TL, TaskItem: TI, Strike: Sk, Node: Nd } = m2
                const tags = getWikiTags().filter(t => t.category !== 'internal')
                const wikiPlugin = createWikiTagPlugin(tags, m2)
                const clockNode2 = createClockNode(m2)
                editor = new Ed({
                    element: editorEl,
                    extensions: [
                        SK.configure({history: {depth: 100}, strike: false}),
                        Sk,
                        Md.configure({indentation: {style: 'space', size: 2}}),
                        TL,
                        TI.configure({nested: true}),
                        clockNode2,
                        wikiPlugin,
                    ],
                    content: md,
                    contentType: 'markdown',
                    autofocus: 'end',
                })
                const mgr2 = editor.markdown
                if (mgr2 && mgr2.escapeMarkdownSyntax) {
                    mgr2.escapeMarkdownSyntax = function (text) {
                        return text.replace(/([\\`*_\[\]])/g, '\\$1')
                    }
                }
                editor.on('selectionUpdate', updateActive)
                updateActive()
            }
        }

        editor.on('selectionUpdate', updateActive)

        wrapper.querySelector('#tip-source-toggle').addEventListener('click', toggleSource)
        wrapper.querySelector('#tip-close').addEventListener('click', closeEditor)

        wrapper.querySelector('#tip-save').addEventListener('click', async () => {
            try {
                const md = getContent()
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
