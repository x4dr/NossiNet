#!/usr/bin/env bash
# One-shot script to vendor the TipTap ESM bundle.
# Run this when you want to update the vendored tip-edit.js.
# Requires: node, npm, npx (esbuild)
set -euo pipefail

OUT="NossiSite/static/lib/tiptap/tip-edit.js"
DIR=$(mktemp -d)
trap 'rm -rf "$DIR"' EXIT

cd "$DIR"
npm init -y > /dev/null
npm install @tiptap/core@latest @tiptap/pm@latest @tiptap/starter-kit@latest @tiptap/markdown@latest

cat > entry.mjs << 'EOF'
export { Editor } from '@tiptap/core'
export { default as StarterKit } from '@tiptap/starter-kit'
export { Markdown } from '@tiptap/markdown'
EOF

npx esbuild entry.mjs --bundle --format=esm --outfile=tip-edit.js

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cp tip-edit.js "$SCRIPT_DIR/$OUT"
echo "Wrote $OUT ($(wc -c < tip-edit.js) bytes)"
