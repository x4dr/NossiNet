# 1. Wiki Tag Rendering in TipTap Editor

**Date**: 2026-06-17

**Status**: Accepted

## Context

Wiki tags (transclusion `[!pagename]`, infolet `[!q:item]`, section-tooltip `[!t:...]`,
clock `[clock|hp|3|6]`, glitch `g~text~g`, invert `i~text~i`, foldable `## !Heading`)
appear as raw text in the TipTap editor. Users must guess what a tag will render as,
and cannot visually distinguish valid from invalid tags.

We need to render these tags visually in the editor while preserving round-trip
markdown serialization. Two approaches exist for ProseMirror: decorations (visual-only
overlays) and custom nodes (schema-level objects).

## Decision

We use a **split approach**:

1. **Simple wiki tags** (transclude, infolet, section-tooltip, glitch, invert, foldable)
   → **Decorations** (`Decoration.inline()` / `Decoration.node()`).

2. **Clock tags** ([clock|...|...|...]) → **Custom inline node** with NodeView.

### Why decorations for simple tags

- The markdown syntax is literally the content of the text node. There is no
  structured data to extract — the tag IS the text.
- Decorations leave the ProseMirror document completely untouched, so the Markdown
  extension serializes back the exact original text with zero effort.
- The "dirty validator" pattern (external JS watches `.tag-dirty` spans, fetches
  validity, swaps CSS classes) is naturally decoupled from ProseMirror's DOM
  management when layered on decoration output.
- Decorations are re-evaluated on every state change, so document edits
  automatically trigger re-decoration.

### Why a custom node for clocks alone

- The clock visualization is rich HTML (rotating tick divs via `generate_clock()`)
  that requires stable DOM — decoration spans are overwritten on every redraw.
- SSE live updates need a persistent NodeView to push data into without the DOM
  being replaced.
- The clock syntax has structured attributes (name, current, total) that map
  naturally to node attributes.
- The cost: we must register parse/serialize rules in the Markdown extension to
  convert `[clock|...]` ↔ clock node.

### Rejected alternatives

**All NodeViews**: Creating a custom node type for every tag class would require
schema changes, parse/serialize rules, and bundle additions for 7+ tag types.
The markdown-to-node mapping for inline tags like `g~text~g` is fragile
(especially across inline marks) and adds complexity with no benefit over
decorations.

**All Decorations**: For clocks, decoration DOM is overwritten on every
ProseMirror state change. Any live-data injection (SSE updates, DB-fetched
clock state) would be lost on the next keystroke. A widget-based approach
(Decoration.replace + factory function with cache) was considered but
requires more external machinery than a NodeView.

## Consequences

- Simple tags round-trip perfectly — the document never changes.
- Glitch and invert decorations are limited to single text nodes (no bold/italic
  inside `g~...~g`). This matches the server-side limitation.
- Clock requires a small TipTap extension (~40 lines) added to
  `tip-wiki-editor.js` and parse/serialize config in the Markdown extension.
- External validator is a separate JS module that observes the editor DOM,
  entirely decoupled from ProseMirror.
