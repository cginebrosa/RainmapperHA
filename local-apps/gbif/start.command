#!/bin/zsh
# Keep the historical file URL so existing browser-local reviews remain reachable.
cd "${0:A:h:h:h}" || exit 1
open "docs/mushrooms/GBIF/snapshot-catalunya-20120619-20260916-full/index.html"
