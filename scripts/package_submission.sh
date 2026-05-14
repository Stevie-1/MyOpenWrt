#!/bin/bash
# package_submission.sh - Build the final source-code zip for assignment submission.
#
# Output: dist/<members>_代码.zip relative to the repo root.
#
# Usage:
#   MEMBERS="张三+李四+王五" ./scripts/package_submission.sh
#
# What's included:
#   README.md, docs/, traffic-monitor/, firewall-scripts/, backend/,
#   frontend/ (src + dist if present), scripts/, test/
#
# What's excluded:
#   node_modules/, __pycache__/, .venv/, build/, .git/, .vscode/, .idea/,
#   *.pcap, *.log, *.img, *.vmdk, *.iso, *.mp4, *.mov

set -euo pipefail

MEMBERS="${MEMBERS:-成员姓名}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/dist"
ZIP_NAME="${MEMBERS}_代码.zip"

mkdir -p "${OUT_DIR}"
rm -f "${OUT_DIR}/${ZIP_NAME}"

cd "${REPO_ROOT}"

EXCLUDES=(
    -x "*/node_modules/*"
    -x "*/__pycache__/*"
    -x "*/.venv/*"
    -x "*/.pytest_cache/*"
    -x "*/build/*"
    -x "*/bin/*"
    -x "*/.git/*"
    -x "*/.vscode/*"
    -x "*/.idea/*"
    -x "*.pyc"
    -x "*.log"
    -x "*.pcap"
    -x "*.pcapng"
    -x "*.img"
    -x "*.vmdk"
    -x "*.iso"
    -x "*.mp4"
    -x "*.mov"
    -x "dist/*"
)

INCLUDES=(
    README.md
    .gitignore
    .gitattributes
    docs
    traffic-monitor
    firewall-scripts
    backend
    scripts
    test
)

# frontend may not exist yet (initialized by partner B); include if present
if [ -d frontend ]; then
    INCLUDES+=(frontend)
fi

if ! command -v zip >/dev/null 2>&1; then
    echo "ERROR: 'zip' command not found. Install with: sudo apt install zip" >&2
    exit 1
fi

echo "==> zipping into ${OUT_DIR}/${ZIP_NAME}"
zip -r "${OUT_DIR}/${ZIP_NAME}" "${INCLUDES[@]}" "${EXCLUDES[@]}"

echo "==> done."
ls -lh "${OUT_DIR}/${ZIP_NAME}"
