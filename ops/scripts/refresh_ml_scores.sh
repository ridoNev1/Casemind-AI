#!/bin/bash
# Simple helper script to refresh ML scores cache.
# Intended to be invoked from cron/CI after ETL pipeline finishes.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${REPO_DIR}/.venv"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Virtualenv not found at ${VENV_DIR}. Please create it before scheduling this script." >&2
  exit 1
fi

source "${VENV_DIR}/bin/activate"
cd "${REPO_DIR}"

python -m ml.pipelines.refresh_ml_scores --top-k "${REFRESH_TOP_K:-50}"

deactivate
