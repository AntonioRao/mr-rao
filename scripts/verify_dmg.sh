#!/usr/bin/env bash
# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
# Monta il .dmg e lancia verify_build sull'eseguibile *dentro* il disco.
# È la prova del file che si condivide, non dell'.app prima di impacchettarlo.
#
#   ./scripts/verify_dmg.sh [percorso.dmg] [interprete-python]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DMG="$(cd "$(dirname "${1:-$ROOT/dist/MrRao-macos-arm64.dmg}")" && pwd)/$(basename "${1:-$ROOT/dist/MrRao-macos-arm64.dmg}")"
PYTHON="${2:-python3}"

if [[ ! -f "$DMG" ]]; then
  echo "ERRORE: manca il dmg: $DMG" >&2
  exit 2
fi

MOUNT="${TMPDIR:-/tmp}/mr-rao-dmg-$$"
mkdir -p "$MOUNT"
staccato=0
stacca() {
  if [[ "$staccato" -eq 0 ]]; then
    hdiutil detach "$MOUNT" -force >/dev/null 2>&1 || true
    rmdir "$MOUNT" 2>/dev/null || true
    staccato=1
  fi
}
trap stacca EXIT

hdiutil attach -nobrowse -readonly -mountpoint "$MOUNT" "$DMG"
EXE="$MOUNT/Mr. Rao.app/Contents/MacOS/MrRao"
if [[ ! -x "$EXE" ]]; then
  echo "ERRORE: nel dmg non c'è Mr. Rao.app/Contents/MacOS/MrRao" >&2
  ls -la "$MOUNT" >&2 || true
  exit 2
fi

echo "montato: $DMG"
echo "eseguo:  $EXE"
"$PYTHON" "$ROOT/scripts/verify_build.py" "$EXE"
