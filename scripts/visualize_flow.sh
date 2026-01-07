#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper to generate Mermaid (.mmd) and optional PNG
# Usage:
#   scripts/visualize_flow.sh <OBJECT_PATH> [--out flow.mmd] [--png] [--labels] [--direction TD|LR|BT]

OBJECT_PATH=${1:-}
if [[ -z "$OBJECT_PATH" ]];
then
  echo "Usage: $0 <OBJECT_PATH> [--out flow.mmd] [--png] [--labels] [--direction TD|LR|BT]" >&2
  exit 1
fi

shift || true

python -m src "$OBJECT_PATH" "$@"
