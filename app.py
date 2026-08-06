import os
import re
import uuid
import email as email_mod
from email import policy
from email.parser import BytesParser
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from markitdown import MarkItDown
from rapidocr_onnxruntime import RapidOCR
import scrubadub
from bs4 import BeautifulSoup

app = Flask(__name__)
# Maximum file size 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'

# Estensioni supportate
ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
    '.html', '.htm', '.csv', '.json', '.xml', '.txt', '.rtf',
    '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp',
    '.eml'
}

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.gif', '.webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

md = MarkItDown()
ocr = RapidOCR()


# ---------------------------------------------------------------------------
#  Parser .EML — Estrae thread email completi e li converte in Markdown
# ---------------------------------------------------------------------------

# Pattern per individuare l'inizio di un messaggio citato (reply)
_REPLY_PATTERNS = [
    # "On Aug 5, 2026, John Doe <john@example.com> wrote:"
    re.compile(r'^\s*On .+wrote:\s*$', re.IGNORECASE | re.MULTILINE),
    # "Il giorno 5 ago 2026, Mario Rossi <mario@esempio.it> ha scritto:"
    re.compile(r'^\s*Il giorno .+ha scritto:\s*$', re.IGNORECASE | re.MULTILINE),
    # "-----Original Message-----"  /  "-------- Messaggio originale --------"
    re.compile(r'^-{3,}\s*(Original Message|Messaggio [Oo]riginale)\s*-{3,}\s*$', re.MULTILINE),
    # Outlook block: "Da: ... Inviato: ... A: ..."
    re.compile(r'^\s*Da:\s*.+\n\s*Inviato:\s*.+\n\s*A:\s*.+', re.MULTILINE),
    # Outlook block: "From: ... Sent: ... To: ..."
    re.compile(r'^\s*From:\s*.+\n\s*Sent:\s*.+\n\s*To:\s*.+', re.MULTILINE),
]


def _html_to_text(html_content):
    """Converte HTML in testo leggibile usando BeautifulSoup."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Rimuovi script e style
        for tag in soup(['script', 'style', 'head']):
            tag.decompose()
        # Sostituisci <br> e <p> con newline
        for br in soup.find_all('br'):
            br.replace_with('\n')
        for p in soup.find_all('p'):
            p.insert_before('\n')
            p.insert_after('\n')
        text = soup.get_text()
        # Pulisci righe vuote multiple
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    except Exception:
        # Fallback brutale se BS4 fallisce
        return re.sub(r'<[^>]+>', '', html_content)


def _get_email_body(msg):
    """Estrae il corpo testuale da un oggetto email (gestisce multipart)."""
    if msg.is_multipart():
        text_parts = []
        html_parts = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            # Salta gli allegati
            if 'attachment' in content_disposition:
                continue
            try:
                payload = part.get_content()
            except Exception:
                continue
            if isinstance(payload, str):
                if content_type == 'text/plain':
                    text_parts.append(payload)
                elif content_type == 'text/html':
                    html_parts.append(payload)
        # Preferisci text/plain, fallback su HTML convertito
        if text_parts:
            return '\n\n'.join(text_parts)
        if html_parts:
            return _html_to_text('\n'.join(html_parts))
        return None
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_content()
        except Exception:
            return None
        if isinstance(payload, str):
            if content_type == 'text/html':
                return _html_to_text(payload)
            return payload
        return None


def _split_thread(body):
    """Divide il corpo dell'email in segmenti di conversazione (messaggio più recente → più vecchio)."""
    segments = []
    remaining = body

    for pattern in _REPLY_PATTERNS:
        match = pattern.search(remaining)
        if match:
            # Tutto prima del match è il messaggio corrente
            before = remaining[:match.start()].strip()
            if before:
                segments.append(before)
            # Il match + tutto dopo è il messaggio citato, proviamo a splittare ricorsivamente
            remaining = remaining[match.start():]
            # Rimuovi le ">" di citazione per rendere leggibile
            break

    if not segments:
        # Nessun pattern trovato, il body è un singolo messaggio
        segments.append(remaining.strip())
    else:
        # Aggiungi il resto (potenzialmente con altri livelli di citazione)
        # Rimuovi i ">" all'inizio di ogni riga per le citazioni
        cleaned = []
        for line in remaining.split('\n'):
            stripped = line.lstrip()
            if stripped.startswith('> '):
                cleaned.append(stripped[2:])
            elif stripped.startswith('>'):
                cleaned.append(stripped[1:])
            else:
                cleaned.append(line)
        cleaned_text = '\n'.join(cleaned)

        # Ricorsione: prova a splittare ulteriormente le citazioni
        sub_segments = _split_thread(cleaned_text)
        segments.extend(sub_segments)

    return segments


def _list_attachments(msg):
    """Elenca gli allegati presenti nel messaggio."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = str(part.get('Content-Disposition', ''))
            if 'attachment' in content_disposition:
                fname = part.get_filename() or '(allegato senza nome)'
                size = len(part.get_payload(decode=True) or b'')
                attachments.append((fname, size))
    return attachments


def parse_eml(filepath):
    """Legge un file .eml e produce un documento Markdown strutturato con l'intero thread."""
    with open(filepath, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

    md_lines = []

    # Intestazione principale
    subject = msg['subject'] or '(nessun oggetto)'
    from_addr = msg['from'] or '(mittente sconosciuto)'
    to_addr = msg['to'] or '(destinatario sconosciuto)'
    cc_addr = msg.get('cc', '')
    date_str = msg['date'] or '(data sconosciuta)'

    md_lines.append(f"# 📧 {subject}\n")
    md_lines.append(f"| Campo | Valore |")
    md_lines.append(f"|-------|--------|")
    md_lines.append(f"| **Da** | {from_addr} |")
    md_lines.append(f"| **A** | {to_addr} |")
    if cc_addr:
        md_lines.append(f"| **CC** | {cc_addr} |")
    md_lines.append(f"| **Data** | {date_str} |")
    md_lines.append("")

    # Allegati
    attachments = _list_attachments(msg)
    if attachments:
        md_lines.append("### 📎 Allegati")
        for fname, size in attachments:
            size_kb = size / 1024
            md_lines.append(f"- `{fname}` ({size_kb:.1f} KB)")
        md_lines.append("")

    md_lines.append("---\n")

    # Corpo e thread
    body = _get_email_body(msg)
    if body:
        segments = _split_thread(body)
        for i, segment in enumerate(segments):
            if i == 0:
                md_lines.append("### ✉️ Ultimo messaggio\n")
            else:
                md_lines.append(f"\n---\n")
                md_lines.append(f"### 💬 Messaggio precedente #{i}\n")
            # Pulisci righe vuote eccessive
            cleaned = re.sub(r'\n{3,}', '\n\n', segment.strip())
            md_lines.append(cleaned)
            md_lines.append("")
    else:
        md_lines.append("> ⚠️ *Nessun contenuto testuale trovato nel file .eml.*")

    md_lines.append("\n---\n")
    md_lines.append("> 🛡️ *Questo documento è stato anonimizzato automaticamente. "
                    "I dati personali (email, telefoni, nomi) sono stati sostituiti "
                    "con segnaposto per consentire la condivisione sicura con sistemi AI.*")

    return "\n".join(md_lines)


def ocr_pdf_fallback(filepath):
    """Converte le pagine del PDF in immagini e applica OCR su ciascuna.
    Usa pdfplumber per estrarre le immagini delle pagine."""
    try:
        import pdfplumber
        from PIL import Image
        import io

        all_text = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                # Converte la pagina in immagine
                img = page.to_image(resolution=300)
                img_bytes = io.BytesIO()
                img.original.save(img_bytes, format='PNG')
                img_bytes.seek(0)

                # Salva temporaneamente per RapidOCR
                temp_img_path = os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    f"_ocr_page_{i}_{uuid.uuid4().hex[:8]}.png"
                )
                with open(temp_img_path, 'wb') as f:
                    f.write(img_bytes.read())

                try:
                    ocr_result, _ = ocr(temp_img_path)
                    if ocr_result:
                        page_lines = [item[1] for item in ocr_result]
                        all_text.append(f"<!-- Pagina {i + 1} -->\n\n" + "\n\n".join(page_lines))
                finally:
                    # Pulizia immagine temporanea
                    try:
                        os.remove(temp_img_path)
                    except OSError:
                        pass

        if all_text:
            header = "> ℹ️ *Testo estratto tramite OCR (il PDF conteneva immagini scansionate, non testo nativo).*\n\n---\n\n"
            return header + "\n\n---\n\n".join(all_text)
        return None
    except Exception as e:
        print(f"OCR PDF fallback error: {e}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nessun file trovato nella richiesta'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nessun file selezionato'}), 400

    if file:
        # Estrai l'estensione dall'originale PRIMA di secure_filename (che può eliminarla)
        original_ext = os.path.splitext(file.filename)[1].lower() if '.' in file.filename else ''
        filename = secure_filename(file.filename)
        if not filename or filename == '':
            # secure_filename ha rimosso tutto (es. nome in cinese/arabo) → usa UUID + estensione originale
            filename = f"{uuid.uuid4().hex}{original_ext}"

        # Usa sempre l'estensione dell'originale per la validazione
        ext = original_ext if original_ext else os.path.splitext(filename)[1].lower()

        # Validazione estensione
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'error': f'Tipo di file "{ext}" non supportato. Formati accettati: PDF, DOCX, XLSX, PPTX, HTML, CSV, TXT, EML e immagini (PNG, JPG, BMP, TIFF, WebP).'
            }), 400

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            engine = request.form.get('engine', 'auto')
            final_text = None
            is_eml = (ext == '.eml')

            if is_eml:
                # Parser email dedicato
                final_text = parse_eml(filepath)

            elif engine == 'paddleocr' or (engine == 'auto' and ext in IMAGE_EXTENSIONS):
                # OCR per immagini
                ocr_result, _ = ocr(filepath)

                markdown_lines = []
                if ocr_result:
                    for item in ocr_result:
                        markdown_lines.append(item[1])

                final_text = "\n\n".join(markdown_lines) if markdown_lines else None

            else:
                # MarkItDown per documenti
                try:
                    md_result = md.convert(filepath)
                    final_text = md_result.text_content
                except Exception as e:
                    print(f"MarkItDown conversion error: {e}")
                    final_text = None

                # Fallback: se il PDF è vuoto (probabilmente scansione), prova OCR
                if ext == '.pdf' and (not final_text or not final_text.strip()):
                    print("PDF vuoto da MarkItDown, tentativo fallback OCR...")
                    ocr_text = ocr_pdf_fallback(filepath)
                    if ocr_text:
                        final_text = ocr_text

            # Applica filtro privacy: automatico per .eml, opzionale per gli altri
            use_privacy_filter = is_eml or request.form.get('privacy_filter') == 'true'
            if use_privacy_filter and final_text:
                final_text = scrubadub.clean(final_text)

            # Gestisci risultato vuoto
            if not final_text or not final_text.strip():
                final_text = (
                    "> ⚠️ **Nessun testo estratto.**\n>\n"
                    "> Il file caricato non contiene testo riconoscibile.\n>\n"
                    "> **Suggerimenti:**\n"
                    "> - Se è un'immagine, assicurati che il testo sia leggibile e ben illuminato.\n"
                    "> - Se è un PDF, prova a selezionare **PaddleOCR** dal menu motore.\n"
                    "> - Se è un documento protetto da password, rimuovi la protezione prima di caricarlo."
                )

            # Clean up the uploaded file after conversion
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"Error removing temporary file: {e}")

            return jsonify({'markdown': final_text})

        except Exception as e:
            # Clean up the file on error too
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
