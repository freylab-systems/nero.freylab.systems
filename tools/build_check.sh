#!/usr/bin/env bash
# Build this site the way GitHub Pages will, before pushing to it.
#
# The VM has no Ruby, so the build runs in a container pinned to the same
# Jekyll and plugin versions GitHub Pages uses. GitHub Pages ignores the repo
# Gemfile and builds with its own gem set, so the container drops the Gemfile
# rather than resolving it — otherwise bundler fails on the missing
# github-pages gem. Gems are cached in ~/.cache/jekyllgems between runs.
#
#   ./tools/build_check.sh        # output lands in /tmp/nerobuild
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${OUT:-/tmp/nerobuild}"
GEMS="$HOME/.cache/jekyllgems"

mkdir -p "$GEMS" "$OUT"

docker run --rm \
  -v "$REPO":/src:ro \
  -v "$GEMS":/gems \
  -v "$OUT":/out \
  -e GEM_HOME=/gems \
  ruby:3.1 bash -c '
    set -e
    export PATH=/gems/bin:$PATH
    if ! command -v jekyll >/dev/null 2>&1; then
      echo "[installing jekyll 3.10.0 + the github-pages plugin set]"
      gem install --no-document jekyll:3.10.0 jekyll-feed:0.17.0 \
        jekyll-seo-tag:2.8.0 jekyll-sitemap:1.4.0 kramdown-parser-gfm:1.1.0 > /dev/null
    fi
    cp -r /src /site
    cd /site
    rm -f Gemfile Gemfile.lock
    rm -rf _site
    rm -rf /out/* /out/.[!.]* 2>/dev/null || true
    jekyll build --trace --destination /out
  '

echo
echo "built to $OUT:"
find "$OUT" -type f | sort
