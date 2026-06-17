# NossiNet Domain Glossary

## Wiki System

- **Wiki Page** — a markdown document rendered by the wiki subsystem. Each page has a name, body (markdown), and optional metadata.
- **NossiMarkdownProcessor** — the server-side pipeline that transforms raw markdown into themed HTML. Runs pre-processors → markdown core → post-processors.
- **Wiki Tags** — custom inline syntax markers processed by the markdown pipeline (e.g. `[!pagename]`, `[clock|hp|3|6]`, `g~text~g`). Each tag has a `NossiTag` subclass with regex-based matching.
- **Tag Registry** — auto-populated list of `NossiTag` instances, ordered by `priority`. Discovered via `__init_subclass__`.

## TipTap Editor

- **TipTap Editor** — the WYSIWYG markdown editor used for wiki page editing. Wraps ProseMirror with a Markdown extension for parse/serialize.
- **Decoration Plugin** — a ProseMirror plugin using `Decoration.inline()` and `Decoration.node()` to apply visual overlays to the editor content without modifying the underlying document. Used for wiki tag highlighting.
- **External Validator** — a JS component (MutationObserver-based) that watches for `.tag-dirty` elements in the editor DOM, performs async validity checks (DB lookups, page existence), and swaps CSS classes (`.tag-valid` / `.tag-invalid`).
- **Clock Node** — a custom TipTap inline node type representing `[clock|name|current|total]` syntax. Uses a NodeView to render the clock visualization and supports SSE live updates.
- **Tooltip** — a Wikipedia-style rich HTML hover tooltip that displays rendered content for transclusions, infolet queries, and section tooltips.
- **Source Mode** — a toggle in the editor toolbar that switches between the WYSIWYG ProseMirror view and a raw markdown textarea.

## Tag Categories (in-editor)

| Category | Tags | Visual treatment |
|----------|------|-----------------|
| `content` | Transclude, Infolet, SectionTooltip | Blue/accent tint. Tooltip shows rendered content. Valid → accent, invalid → warning. |
| `interactive` | Clock | Green/text tint. Custom NodeView renders clock. Valid → green, invalid → warning. |
| `text` | Glitch, Invert | Purple tint. Static CSS effects (glitch frame, invert filter). Single text node only. |
| `layout` | Foldable | Midground border around heading block. `::before` "folded" label. |
| `internal` | HeaderFix, LinkValidator | Not exposed in editor UI. |

## Glitch/Invert Limitations

- **Single text node only**: `g~text~g` and `i~text~i` are only decorated when the content does not cross inline mark boundaries (bold, italic). This matches the server-side limitation — the post_process regex also cannot handle HTML-tagged content between tildes.
