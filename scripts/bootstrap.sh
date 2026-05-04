#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.txt
mkdir -p data/bronze data/silver data/gold models checkpoints logs

echo "Bootstrap complete."
