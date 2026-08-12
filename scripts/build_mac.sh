#!/usr/bin/env bash
# Mr. Rao — .app arm64 con firma ad-hoc (gratis).
#
# Da lanciare su un Mac Apple Silicon. Su 8 GB di RAM la build PyInstaller
# può andare in swap: meglio il workflow GitHub Actions (macos.yml).
#
#   chmod +x scripts/build_mac.sh
#   ./scripts/build_mac.sh
#
# Non richiede Apple Developer Program. Gatekeeper avvisa al primo avvio:
# tasto destro → Apri (dettagli in docs/MACOS.md).
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
find "$APP/Contents" \( -name "*.dylib" -o -name "*.so" \) \
  -exec codesign --force --timestamp=none -s - {} \;
codesign --force --options runtime -s - "$APP"
codesign --verify --strict --verbose=2 "$APP"

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
echo "Apri il .dmg, trascina Mr. Rao in Applicazioni, poi tasto destro → Apri."
echo "Vedi docs/MACOS.md."
