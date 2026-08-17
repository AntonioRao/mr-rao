#!/usr/bin/env bash
# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
# Mr. Rao — .app arm64 con firma ad-hoc (gratis).
#
# Da lanciare su un Mac Apple Silicon. Su 8 GB di RAM la build PyInstaller
# può andare in swap: meglio il workflow GitHub Actions (macos.yml).
#
#   chmod +x scripts/build_mac.sh
#   ./scripts/build_mac.sh
#
# Non richiede Apple Developer Program. Gatekeeper blocca il primo avvio, e si
# sblocca da Impostazioni di Sistema → Privacy e sicurezza → Apri comunque.
# NON da «tasto destro → Apri»: Apple ha tolto quella scorciatoia con macOS 15
# Sequoia (dettagli in docs/MACOS.md).
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
APP="dist/MrRao.app"
DMG="dist/MrRao-macos-arm64.dmg"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Questo script gira solo su macOS." >&2
  exit 2
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "v1 arm64-only: questo Mac è $(uname -m). Serve Apple Silicon." >&2
  exit 2
fi

python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-build.txt

SRC=static/img/logo.png
if [[ ! -f "$SRC" ]]; then
  echo "Manca $SRC" >&2
  exit 2
fi
ICONSET=build/mr-rao.iconset
mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
  sips -z "$s" "$s" "$SRC" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  sips -z $((s * 2)) $((s * 2)) "$SRC" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o build/mr-rao.icns
cp -f build/mr-rao.icns static/img/mr-rao.icns

# Niente UPX: su Mach-O rompe la firma. Separatore --add-data ':' (non ';').
pyinstaller --noconfirm --clean --onedir --windowed --name MrRao \
  --icon build/mr-rao.icns \
  --osx-bundle-identifier com.antoniorao.mrrao \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --hidden-import=mr_rao \
  --hidden-import=mr_rao.routes \
  --hidden-import=mr_rao.converter \
  --hidden-import=mr_rao.eml_parser \
  --hidden-import=mr_rao.ocr_service \
  --hidden-import=mr_rao.privacy \
  --hidden-import=mr_rao.profiles \
  --hidden-import=mr_rao.watch_service \
  --hidden-import=mr_rao.jobs \
  --hidden-import=mr_rao.tray \
  --hidden-import=mr_rao.finestra \
  --hidden-import=mr_rao.cli \
  --hidden-import=webview \
  --hidden-import=webview.platforms.cocoa \
  --collect-all webview \
  --exclude-module tkinter \
  --exclude-module _tkinter \
  --hidden-import=bs4 \
  --hidden-import=rapidocr \
  --hidden-import=docx \
  --hidden-import=pdfplumber \
  --hidden-import=PIL \
  --collect-all rapidocr \
  --collect-all onnxruntime \
  --collect-all markitdown \
  --collect-all magika \
  --collect-submodules mr_rao \
  app.py

# PyInstaller --windowed --name MrRao produce dist/MrRao.app
if [[ ! -d "$APP" ]]; then
  echo "PyInstaller non ha prodotto $APP" >&2
  ls -la dist || true
  exit 2
fi

# verify_build confronta byte-per-byte l'icona del repo. Su Windows sta
# accanto a app/; nel .app va in Resources, prima della firma.
mkdir -p "$APP/Contents/Resources"
cp -f static/img/mr-rao.ico "$APP/Contents/Resources/mr-rao.ico"

# Firma dall'interno verso l'esterno. Niente --deep (deprecato per firmare).
# `-s -` = ad-hoc: gratis, basta al kernel Apple Silicon.
#
# ## Perche' si firma per FORMA e non per estensione
#
# La versione precedente cercava `*.dylib` e `*.so`. Dentro un bundle
# PyInstaller c'e' anche codice Mach-O **senza estensione**, e il piu'
# importante e' proprio il motore: `Frameworks/Python.framework/Versions/3.12/
# Python`. Quel file restava con la firma di chi ha compilato l'interprete
# (python.org: Team ID vero), mentre l'app veniva firmata ad-hoc (nessun Team
# ID). Due identita' diverse nello stesso processo.
#
# Costo misurato, 16/08/2026, su un MacBook Air M1 con macOS 26: l'app non
# parte affatto. dyld rifiuta di mappare l'interprete e stampa
#
#   Failed to load Python shared library '.../Contents/Frameworks/Python'
#   ... not valid for use in process: mapping process and mapped file
#       (non-platform) have different Team IDs
#
# Non e' l'avviso di Gatekeeper -- e' il programma che muore prima di
# esistere, su un disco scaricato dalla pagina delle release.
#
# Quindi si firma tutto cio' che **e'** Mach-O, chiesto a `file`, non tutto
# cio' che si chiama in un certo modo. I framework si firmano alla loro
# versione, che e' l'unita' che macOS valuta.
while IFS= read -r f; do
  file -b "$f" | grep -q "Mach-O" && codesign --force --timestamp=none -s - "$f"
done < <(find "$APP/Contents" -type f)

while IFS= read -r fw; do
  for v in "$fw"/Versions/*/; do
    [[ -d "$v" ]] && codesign --force --timestamp=none -s - "$v"
  done
done < <(find "$APP/Contents" -type d -name "*.framework")

# **Niente `--options runtime`.** L'hardened runtime accende la *library
# validation*, cioe' la regola che pretende un'unica identita' per tutto il
# codice caricato -- ed e' esattamente la regola che uccideva l'app. Serve per
# la notarizzazione, che qui non si fa (99 USD/anno, scelta gia' presa e
# spiegata in docs/MACOS.md): tenerlo significava pagarne il prezzo senza
# incassarne il beneficio.
codesign --force -s - "$APP"
codesign --verify --strict --verbose=2 "$APP"

# Controllo positivo: dopo la firma NESSUN binario annidato deve portare un
# Team ID. Se ne resta uno, l'app non parte -- e senza questo controllo lo si
# scopre da un utente, non dalla build. Il `verify_build` piu' sotto lancia
# l'eseguibile e prenderebbe il caso, ma solo se il macOS che costruisce e'
# severo quanto quello che scarica: la regola si e' stretta col tempo, e una
# build su un sistema piu' vecchio resterebbe verde.
estranei=0
while IFS= read -r f; do
  if file -b "$f" | grep -q "Mach-O"; then
    if codesign -dv --verbose=4 "$f" 2>&1 | grep -q "^TeamIdentifier=[^n]"; then
      echo "FIRMA ESTRANEA: $f" >&2
      estranei=$((estranei + 1))
    fi
  fi
done < <(find "$APP/Contents" -type f)
if [[ "$estranei" -gt 0 ]]; then
  echo "$estranei binari annidati hanno un Team ID diverso dall'app: non partirebbe." >&2
  exit 2
fi
echo "firma: nessun Team ID estraneo fra i binari annidati."

# Disco: .app + scorciatoia Applicazioni. Si apre e si trascina, niente Estrai.
# ditto (non cp -R) tiene symlink e bit di esecuzione del bundle.
STAGING=dist/dmg
rm -rf "$STAGING"
mkdir -p "$STAGING"
ditto "$APP" "$STAGING/Mr. Rao.app"
ln -s /Applications "$STAGING/Applications"
rm -f "$DMG"
hdiutil create -volname "Mr. Rao" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
codesign --force --timestamp=none -s - "$DMG" || true
( cd dist && shasum -a 256 MrRao-macos-arm64.dmg > SHA256SUMS-macos.txt )

echo
echo "ok: $DMG"
echo "Apri il .dmg e trascina Mr. Rao in Applicazioni. Il primo avvio verra'"
echo "bloccato: sbloccalo da Impostazioni di Sistema > Privacy e sicurezza >"
echo "Apri comunque. Il vecchio 'tasto destro > Apri' non esiste piu' da"
echo "macOS 15 Sequoia. Vedi docs/MACOS.md."
