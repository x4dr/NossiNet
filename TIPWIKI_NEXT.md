# TipTap Wiki Editor — Next Steps Plan

## Status

- [x] Basic WYSIWYG editor
- [x] Wiki tag dropdown insert
- [x] Checkbox round-trip (TaskList + TaskItem bundle)
- [x] Source mode toggle
- [ ] Custom tag decorations (this plan)
- [ ] Multi-user collaboration (future)

---

## 2. Render Custom Tags in Editor (medium priority)

**Problem:** `[!q:sword]`, `[clock|hp|3|6]`, `[!endworld/systems]` appear as raw text.
No visual feedback. Cannot distinguish valid from invalid tags.

**Approach — Split architecture:**

| Tag type | Mechanism | Why |
|----------|-----------|-----|
| Transclude, Infolet, SectionTooltip, Glitch, Invert | `Decoration.inline()` / `Decoration.node()` | Visual-only overlay. Zero impact on serialization. |
| Clock | Custom inline Node with NodeView | Rich HTML rendering needs stable DOM. SSE live updates. |
| Foldable (`## !Heading`) | `Decoration.node()` + CSS `::before` | Border + "folded" label. Pure CSS. |

External MutationObserver-based validator watches `.tag-dirty` spans, fetches async
validity (DB lookups, page existence), swaps to `.tag-valid` / `.tag-invalid`.

### 2a. Serve regex patterns from Python

Add `pattern` field to `to_dict()`. Serve Python regex strings verbatim; JS performs
mechanical `s/(?P<(.+?)>)/(?<$1>)/g` replacement for named groups.

**Flags:** served as separate array (e.g., `flags: ["i"]` for ignorecase).

**Tags to pattern:**

| Tag | Regex | Flags | Notes |
|-----|-------|-------|-------|
| Transclude | `\[!(?![tq]:)(?P<page>[^#|\]]+?)(?:#(?P<fragment>[^|\]]*?))?(?:\|(?P<text>[^\]]*?))?\]` | none | |
| SectionTooltip | `\[!t:(?P<spec>[^\]]+?)\]` | `i` | |
| Infolet | `\[!q:(?P<name>.*?)\]` | `i` | |
| Clock (inline) | `\[clock\|(?P<name>.*?)\|(?P<current>\d+)\|(?P<total>\d+)\]` | none | Handled by custom node, not decoration |
| Clock (linked) | `\[clock\|(?P<name>.*?)@(?P<page>.*?)\]` | none | Same |
| Glitch | `g~([^~]+)~(?:(?:([^~]+)~g)\|g)` | none | Single text node only |
| Invert | `i~([^~]+)~i` | none | Single text node only |
| Foldable | no regex — match heading nodes whose text starts with `!` | — | Handled in decoration plugin directly |

### 2b. Decoration Plugin (WikkiTags extension)

A TipTap extension that registers a ProseMirror plugin with `props.decorations(state)`:

1. Walk doc text nodes
2. For each text node, test all tag patterns
3. For matches, create `Decoration.inline()` with class `tag-dirty <tag-id>`
4. For foldable: `Decoration.node()` on heading blocks whose first text child starts with `!`

### 2c. External Validator (wiki-tag-validator.js)

- `MutationObserver` on `.ProseMirror` watching for `.tag-dirty` insertion
- For each `.tag-dirty`: fetch validity via API endpoint
  - Transclude: check `WikiPage.locate(page)`
  - Infolet: check `Item.item_cache`
  - SectionTooltip: check page existence
  - Clock: check DB for named clock
- On success: swap to `.tag-valid`, inject `data-content` for tooltip
- On failure: swap to `.tag-invalid`

### 2d. Tooltip System

- Wikipedia-style rich HTML tooltip on hover
- Shared component reads `data-tooltip-content` from the decorated span
- For transclusions/section-tooltips: fetched rendered content inserted via validator
- For infolet: fetched item description

### 2e. Visual Design

| State | CSS treatment |
|-------|---------------|
| `.tag-dirty` | Subtle gray/pending tint |
| `.tag-valid .transclusion` | Accent color (cyan/blue) background, rounded pill |
| `.tag-valid .infolet` | Accent color background, rounded pill |
| `.tag-valid .clock` | Text color tint background |
| `.tag-valid .glitch` | Purple tint, glitch CSS effect (bottom half static) |
| `.tag-valid .invert` | `filter: invert(1)` |
| `.tag-invalid` | Warning color border |
| `.foldable-heading` | Midground border, `::before` "folded" label |

All colors use `color-mix(in srgb, var(--variable), transparent X%)`.

### 2f. Clock Custom Node

TipTap inline node extending `Node.create()`:

```javascript
const ClockNode = Node.create({
  name: 'clock',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes: { name: {}, current: {}, total: {}, page: {} },
  renderHTML: ({ node }) => generateClockHTML(node.attrs),
  parseHTML: [...],  // from stored mark
  renderMarkdown: { /* serialize to [clock|...] */ },
  parseMarkdown: { /* match [clock|...] and convert to node */ },
})
```

Registered in editor extensions alongside StarterKit. SSE handler calls
`view.dispatch(tr)` to update attrs when clock data changes.

### 2g. Round-trip safety

- Decorations: document untouched → serializer sees raw text ✅
- Clock node: explicit `renderMarkdown` callback → `[clock|...]` ✅
- Foldable: heading text unchanged, `!` prefix remains ✅

---

## 3. Source Mode Toggle ✅ (done)

## 4. Multi-user Collaboration (future)

Yjs + y-websocket or custom SSE provider. Not planned yet.

---

## Files to change

| File | Change |
|------|--------|
| `NossiPack/markdown/base.py` | Add `pattern` and `flags` fields to `NossiTag.to_dict()` |
| `NossiPack/markdown/tags/*.py` | Set `pattern` on each tag class |
| `NossiSite/static/tip-wiki-editor.js` | Add WikkiTags decoration plugin + Clock node extension |
| `NossiSite/static/wiki-tag-validator.js` | New file: external validator + tooltip system |
| `NossiSite/static/tip-wiki-editor.css` | Decoration styles, foldable styles, tooltip styles |
| `NossiSite/static/wiki.css` | Possibly shared tooltip styles |
| `NossiSite/wiki.py` | New endpoint: `/tag-validate` for async validity checks |
