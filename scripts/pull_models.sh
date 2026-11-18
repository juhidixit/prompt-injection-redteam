#!/usr/bin/env bash
# Download GGUF weights for open-weight models from Docker Hub's `ai/` namespace
# (OCI artifacts produced by Docker Model Runner). Useful where huggingface.co is
# unreachable. Usage: scripts/pull_models.sh ai/qwen2.5:3B-Q4_K_M [more ...]
# Weights land in ${MODELS_DIR:-models}/<name>-<tag>.gguf
set -euo pipefail
OUT="${MODELS_DIR:-models}"
mkdir -p "$OUT"
for ref in "$@"; do
  repo="${ref%%:*}"; tag="${ref##*:}"
  name="$(basename "$repo")-$tag.gguf"
  if [[ -s "$OUT/$name" ]]; then echo "exists: $OUT/$name"; continue; fi
  tok=$(curl -fsS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$repo:pull" \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
  manifest=$(curl -fsS -H "Authorization: Bearer $tok" \
        -H "Accept: application/vnd.oci.image.manifest.v1+json" \
        "https://registry-1.docker.io/v2/$repo/manifests/$tag")
  digest=$(python3 -c '
import sys, json
m = json.loads(sys.argv[1])
layers = [l for l in m["layers"] if "gguf" in l["mediaType"]]
print(max(layers, key=lambda l: l["size"])["digest"])' "$manifest")
  echo "downloading $ref -> $OUT/$name ($digest)"
  curl -fsSL --retry 5 -H "Authorization: Bearer $tok" -o "$OUT/$name.part" \
       "https://registry-1.docker.io/v2/$repo/blobs/$digest"
  mv "$OUT/$name.part" "$OUT/$name"
done
