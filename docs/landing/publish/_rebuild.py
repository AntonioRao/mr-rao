from pathlib import Path
import re
import hashlib
import base64

root = Path(__file__).resolve().parent
src = (root.parent / "01-protocollo-zero.html").read_text(encoding="utf-8")

# no inline style attributes (allow 'stylesheet' word only via different pattern)
if re.search(r"""\sstyle\s*=""", src):
    raise SystemExit("inline style attributes still present in source")
if "el.style" in src:
    raise SystemExit("el.style still present in source")

html = src.replace("../../static/img/logo.svg", "assets/logo.svg").replace(
    "../../static/img/favicon.svg", "assets/favicon.svg"
)
(root / "index.html").write_text(html, encoding="utf-8", newline="\n")

styles = re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I)
scripts = re.findall(
    r"<script(?![^>]*\bsrc=)(?:\s[^>]*)?>(.*?)</script>", html, re.S | re.I
)


def sh(s: str) -> str:
    return (
        "sha256-"
        + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode()
    )


style_h, script_h = sh(styles[0]), sh(scripts[0])
print("STYLE", style_h)
print("SCRIPT", script_h)

hdr_path = root / "_headers"
hdr = hdr_path.read_text(encoding="utf-8")
hdr = re.sub(
    r"script-src 'self' 'sha256-[^']+'",
    f"script-src 'self' '{script_h}'",
    hdr,
)
hdr = re.sub(
    r"style-src 'self' 'sha256-[^']+'",
    f"style-src 'self' '{style_h}'",
    hdr,
)
hdr_path.write_text(hdr, encoding="utf-8", newline="\n")
print("OK wrote index.html + _headers")
