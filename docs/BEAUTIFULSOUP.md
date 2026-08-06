# BeautifulSoup4 — a cosa serve in Mr. Rao

## In una frase

**BeautifulSoup4** (`bs4`) è una libreria Python per **analizzare e navigare HTML/XML**. In Mr. Rao la usiamo per trasformare il corpo HTML delle email (e pezzi HTML) in **testo leggibile**, prima di produrre il Markdown.

## Perché serve

Molte email `.eml` non hanno solo `text/plain`: contengono `text/html` (Outlook, Gmail, newsletter). Se leggessimo l’HTML grezzo otterresti tag, stili e script nel Markdown:

```html
<div style="font-family:Arial"><b>Ciao</b><br>Vedi allegato</div>
```

Con BeautifulSoup:

1. Si carica l’HTML in un albero DOM
2. Si rimuovono `script`, `style`, `head`
3. Si traducono `<br>` / `<p>` in a capo
4. Si estrae solo il testo utile

Risultato:

```text
Ciao
Vedi allegato
```

## Dove è integrata

| File | Uso |
|------|-----|
| `mr_rao/eml_parser.py` → `html_to_text()` | Corpo HTML delle email |
| `requirements.txt` | Dipendenza dichiarata: `beautifulsoup4>=4.12.0` |
| `Installa Mr Rao.bat` | Installa tutto via `pip install -r requirements.txt` |

## Dipendenza correlata

BeautifulSoup usa un parser; di default `html.parser` (stdlib, zero extra). Non serve `lxml` per Mr. Rao.

## Installazione manuale

```bash
pip install beautifulsoup4>=4.12.0
```

Oppure, dalla cartella del progetto (consigliato):

```bat
Installa Mr Rao.bat
```
