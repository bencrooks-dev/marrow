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
  # --load(-media)-error-handling=ignore: don't fail the whole render when a
  # remote asset (e.g. a status badge whose repo/package doesn't exist yet)
  # 404s. Without this, wkhtmltopdf exits non-zero on ContentNotFoundError and
  # `set -e` aborts the script — which is what broke this job after the rename.
  pandoc "$doc" \
    --from gfm \
    --pdf-engine=wkhtmltopdf \
    --pdf-engine-opt=--load-error-handling --pdf-engine-opt=ignore \
    --pdf-engine-opt=--load-media-error-handling --pdf-engine-opt=ignore \
    --metadata title="$name" \
    --toc --toc-depth=2 \
    --highlight-style=tango \
    -V margin-top=18mm -V margin-bottom=18mm \
    -V margin-left=16mm -V margin-right=16mm \
    -o "$OUT/$name.pdf"
  rendered=$((rendered + 1))
done

echo "rendered $rendered document(s) -> $OUT"
