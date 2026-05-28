#!/usr/bin/env bash
# Render the marrow / ARI documentation set to PDF with pandoc.
#
# Used by .github/workflows/docs-pdf.yml. Requires: pandoc + wkhtmltopdf
# (an HTML-based PDF engine — chosen over LaTeX because several docs contain
# unicode box-drawing diagrams in code fences that LaTeX fonts mishandle).
#
# Local use:  sudo apt-get install -y pandoc wkhtmltopdf fonts-dejavu
#             xvfb-run -a bash scripts/render-pdfs.sh
set -euo pipefail

OUT="docs/pdf"
mkdir -p "$OUT"

# The pitch DECK is rendered separately by Marp (see the workflow); these are
# the prose documents.
DOCS=(
  "ARI-SPEC.md"
  "THREAT-MODEL.md"
  "SECURITY.md"
  "STABILITY.md"
  "ROADMAP.md"
  "GOVERNANCE.md"
  "CONFORMANCE.md"
  "README.md"
  "docs/ari-strategy.md"
  "docs/ari-rfc-process.md"
  "docs/market-research.md"
  "docs/pitch/one-pager.md"
  "ari-conformance/README.md"
)

rendered=0
for doc in "${DOCS[@]}"; do
  if [ ! -f "$doc" ]; then
    echo "skip (missing): $doc"
    continue
  fi
  # Flatten path into a unique output name (avoids README.md collisions).
  name="$(echo "${doc%.md}" | tr '/' '-')"
  echo "rendering $doc -> $OUT/$name.pdf"
  # Strip remote images (CI / license / PyPI status badges) before rendering.
  # wkhtmltopdf fetches them over the network and aborts the whole run with
  # "Exit with code 1 due to network error: ContentNotFoundError" when one 404s
  # — e.g. badges pointing at the not-yet-renamed repo / unpublished package.
  # --load-error-handling=ignore does NOT override that exit in wkhtmltopdf
  # 0.12.6, so we remove the images instead; they add nothing to a PDF.
  src="$(mktemp --suffix=.md)"
  sed -E 's#!\[[^]]*\]\(https?://[^)]*\)##g; s#<img[^>]*src="https?://[^"]*"[^>]*/?>##g' "$doc" > "$src"
  pandoc "$src" \
    --from gfm \
    --pdf-engine=wkhtmltopdf \
    --metadata title="$name" \
    --toc --toc-depth=2 \
    --highlight-style=tango \
    -V margin-top=18mm -V margin-bottom=18mm \
    -V margin-left=16mm -V margin-right=16mm \
    -o "$OUT/$name.pdf"
  rm -f "$src"
  rendered=$((rendered + 1))
done

echo "rendered $rendered document(s) -> $OUT"
