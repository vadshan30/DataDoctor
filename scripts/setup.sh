#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Activate with: source backend/venv/bin/activate"
