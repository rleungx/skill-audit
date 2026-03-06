#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_bin="${PYTHON:-python3}"
dist_dir="${1:-$repo_root/dist}"

if ! "$python_bin" -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller is not installed for $python_bin." >&2
  echo "Run: $python_bin -m pip install -e '.[binary]'" >&2
  exit 1
fi

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/skill-audit-build.XXXXXX")"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

entry_script="$tmp_dir/entry.py"
pyinstaller_config_dir="$tmp_dir/pyinstaller-config"
cat > "$entry_script" <<'EOF'
from skill_audit.cli import main

if __name__ == "__main__":
    main()
EOF

mkdir -p "$dist_dir"
mkdir -p "$pyinstaller_config_dir"

PYINSTALLER_CONFIG_DIR="$pyinstaller_config_dir" \
"$python_bin" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name skill-audit \
  --distpath "$dist_dir" \
  --workpath "$tmp_dir/build" \
  --specpath "$tmp_dir/spec" \
  --paths "$repo_root/src" \
  --add-data "$repo_root/src/skill_audit/assets/report.ts:skill_audit/assets" \
  "$entry_script"

echo "Built $dist_dir/skill-audit"
