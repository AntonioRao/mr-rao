# Mr. Rao -- Copyright (c) 2026 Antonio Andrea Rao.
# SPDX-License-Identifier: AGPL-3.0-or-later
# Software libero: puoi ridistribuirlo e/o modificarlo secondo i termini della
# GNU Affero General Public License pubblicata dalla Free Software Foundation,
# versione 3 o (a tua scelta) successiva. Vedi LICENSE nella radice del repository.
"""Misura com'e' fatto il degrado di una scansione **vera**.

A cosa serve, e perche' esiste
------------------------------

`bench_scansioni.py` degrada le pagine con dei numeri:

    UFFICIO   = Profilo(grana_toner=34.0, inchiostro=0, sfocatura=0.8, ...)
    FOTOCOPIA = Profilo(grana_toner=48.0, inchiostro=-18, sfocatura=1.3, ...)

**Quei numeri li ho scelti io.** Sono plausibili e non sono misurati da
niente: e' il senso della riga «la carta e' simulata» rimasta aperta in A.9.
Questo script li sostituisce con valori **ricavati da scansioni reali**.

Cosa questo script NON fa, ed e' bene dirlo subito: non chiude A.9. Per
contare quanti dati personali sopravvivono serve sapere quali c'erano, cioe'
serve una pagina scritta da noi; nessun corpus al mondo ha i nostri codici
fiscali inventati su carta davvero scansionata. Questo script sposta il
degrado da «inventato» a «misurato», che e' una cosa piu' piccola e
verificabile.

Il corpus
---------

Le scansioni reali **non stanno nel repository** (`corpora-locali/` e'
escluso): la licenza di FUNSD permette ricerca e didattica ma non la
ridistribuzione, e sono documenti di persone reali. Nel repository entrano i
parametri e questo script. Chi vuole rifare la misura scarica il corpus.

    corpora-locali/funsd/*.png      (199 moduli scansionati veri)

La regola che questo script si applica addosso
----------------------------------------------

**Un estimatore che non sa ritrovare un valore noto non misura niente.**
Prima di toccare il corpus vero, `autoprova()` costruisce pagine sintetiche
con sfocatura, rumore e inclinazione **noti** e verifica che le stime li
ritrovino. Se non ci riesce, lo script si ferma: meglio nessun numero che un
numero inventato con l'aria di essere misurato.

L'autoprova fa anche da **taratura**: l'acutanza non e' un sigma, e la
corrispondenza fra le due si ricava dalle pagine a sfocatura nota invece che
da una formula sperata.

Uso:
    venv\\Scripts\\python scripts\\misura_degrado_reale.py
    venv\\Scripts\\python scripts\\misura_degrado_reale.py --corpus <cartella>
"""
from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RADICE = Path(__file__).resolve().parent.parent
CORPUS_PREDEFINITO = RADICE / "corpora-locali" / "funsd"

# Sotto questa soglia un riquadro e' considerato carta, non testo. Serve a
# misurare il rumore dove non c'e' inchiostro: misurarlo sui caratteri
# darebbe la varianza del testo, non quella del sensore.
QUANTILE_CARTA = 0.75


@dataclass
class Misura:
    """Cosa si riesce a leggere da una pagina scansionata."""

    livello_carta: float      # 0-255, quanto e' chiaro il bianco vero
    livello_inchiostro: float  # 0-255, quanto e' nero il nero vero
    contrasto: float          # separazione fra i due, normalizzata
    rumore: float             # deviazione standard sulla carta pulita
    acutanza: float           # gradiente medio sui bordi, normalizzato
    inclinazione: float       # gradi, positivo = orario


# ---------------------------------------------------------------- stime

def _livelli(a: np.ndarray) -> tuple[float, float]:
    """I due picchi dell'istogramma: la carta e l'inchiostro.

    Non si usano il minimo e il massimo — su una scansione vera basta un
    granello nero o una piega bianca per spostarli entrambi. Si usano due
    percentili robusti.
    """
    carta = float(np.percentile(a, 95))
    inchiostro = float(np.percentile(a, 2))
    return carta, inchiostro


def _rumore_su_carta(a: np.ndarray, livello_carta: float, lato: int = 16) -> float:
    """La deviazione standard dove c'e' solo carta.

    Si taglia la pagina in riquadri, si tengono quelli abbastanza chiari da
    non contenere testo, e si prende la **mediana** delle loro deviazioni
    standard. La mediana e non la media: qualche riquadro prendera' comunque
    un bordo di carattere, e la media ne verrebbe trascinata.
    """
    h, w = a.shape
    h -= h % lato
    w -= w % lato
    if h < lato or w < lato:
        return float("nan")
    riquadri = a[:h, :w].reshape(h // lato, lato, w // lato, lato)
    riquadri = riquadri.transpose(0, 2, 1, 3).reshape(-1, lato * lato)

    medie = riquadri.mean(axis=1)
    # «Abbastanza chiaro da essere carta»: vicino al livello della carta.
    e_carta = medie >= livello_carta - 12
    if e_carta.sum() < 8:
        e_carta = medie >= np.quantile(medie, QUANTILE_CARTA)
    return float(np.median(riquadri[e_carta].std(axis=1)))


def _acutanza(a: np.ndarray, contrasto: float) -> float:
    """Quanto sono ripidi i bordi dei caratteri.

    Non e' un sigma di sfocatura e non va spacciata per tale: e' il gradiente
    medio **sui soli pixel di bordo**, normalizzato dal contrasto della
    pagina. Serve perche' e' monotona nella sfocatura — piu' e' sfocato, piu'
    scende — e l'autoprova la converte in sigma con una taratura, invece che
    con una formula sperata.

    La normalizzazione per il contrasto e' necessaria: una pagina sbiadita ha
    gradienti piu' bassi anche se e' perfettamente a fuoco, e senza dividere
    si scambierebbe lo sbiadimento per sfocatura.
    """
    gy, gx = np.gradient(a.astype(np.float32))
    g = np.hypot(gx, gy)
    if contrasto <= 1e-6:
        return float("nan")
    # I pixel di bordo: quelli col gradiente nel quartile alto. Gli altri
    # sono carta piatta o interno del carattere, e diluirebbero la media.
    soglia = np.quantile(g, 0.99)
    bordi = g >= soglia
    if bordi.sum() < 32:
        return float("nan")
    return float(g[bordi].mean() / (contrasto * 255.0))


def _inclinazione(a: np.ndarray, ampiezza: float = 4.0, passo: float = 0.2) -> float:
    """L'angolo a cui le righe di testo sono piu' «righe».

    Si ruota di prova e si guarda la varianza del profilo orizzontale: quando
    le righe sono dritte, le somme per riga alternano molto fra righe di
    testo e interlinea, e la varianza e' massima.
    """
    piccola = a
    if max(a.shape) > 900:
        fattore = 900 / max(a.shape)
        im = Image.fromarray(a).resize(
            (max(1, int(a.shape[1] * fattore)), max(1, int(a.shape[0] * fattore))),
            Image.BILINEAR,
        )
        piccola = np.asarray(im)

    inchiostro = 255.0 - piccola.astype(np.float32)
    base = Image.fromarray(inchiostro.astype(np.uint8))

    migliore, migliore_var = 0.0, -1.0
    ang = -ampiezza
    while ang <= ampiezza + 1e-9:
        ruotata = np.asarray(
            base.rotate(ang, resample=Image.BILINEAR, fillcolor=0), dtype=np.float32
        )
        profilo = ruotata.sum(axis=1)
        var = float(profilo.var())
        if var > migliore_var:
            migliore_var, migliore = var, ang
        ang += passo
    # `migliore` e' la rotazione (antioraria, convenzione PIL) che RADDRIZZA
    # la pagina. Una pagina inclinata in senso orario si raddrizza girando
    # in antiorario della stessa quantita', quindi l'inclinazione oraria
    # coincide con `migliore` — senza cambio di segno.
    #
    # La prima versione restituiva `-migliore`, e l'autoprova l'ha presa:
    # modulo esatto, segno rovesciato su tutti e tre gli angoli di prova.
    # E' il genere di errore che su un corpus vero non si vede, perche' le
    # inclinazioni sono distribuite attorno allo zero e la mediana del
    # valore assoluto non cambia.
    return migliore


def misura(img: Image.Image) -> Misura:
    """Tutte le stime su una pagina."""
    a = np.asarray(img.convert("L"))
    carta, inchiostro = _livelli(a)
    contrasto = max(0.0, (carta - inchiostro) / 255.0)
    return Misura(
        livello_carta=carta,
        livello_inchiostro=inchiostro,
        contrasto=contrasto,
        rumore=_rumore_su_carta(a, carta),
        acutanza=_acutanza(a, contrasto),
        inclinazione=_inclinazione(a),
    )


# ------------------------------------------------------------- autoprova

TESTO_PROVA = [
    "Spett.le Amministrazione Comunale",
    "Oggetto: richiesta di accesso agli atti",
    "",
    "Il sottoscritto, in qualita' di parte interessata, chiede",
    "copia dei documenti relativi al procedimento in oggetto.",
    "Riferimento pratica 2026/0184 del 12 marzo.",
    "",
    "Recapito: 06 5555 0100 - protocollo interno 0123456789",
    "Coordinate: IT60X0542811101000000123456",
    "",
    "Distinti saluti",
]


def _pagina_sintetica(
    font_path: str, larghezza: int = 1000, carta: int = 255, inchiostro: int = 0
) -> Image.Image:
    """Una pagina pulita su cui applicare degradi noti.

    `carta` e `inchiostro` sono regolabili per una ragione precisa, scoperta
    dall'autoprova. Su una pagina bianca pura (255) il rumore gaussiano viene
    **tosato dal tetto**: la meta' sopra 255 non esiste, e la deviazione
    standard che si osserva e' circa il 59% di quella iniettata. La stima
    sembrava sbagliata del 40% ed era invece corretta — era il banco di prova
    a chiedere di ritrovare un valore che nell'immagine non c'era piu'.

    Per provare il rumore si usa quindi una carta lontana dai due estremi.
    Non e' un trucco per far passare la prova: una scansione vera la carta a
    255 pieno non ce l'ha quasi mai.
    """
    font = ImageFont.truetype(font_path, 20)
    altezza = 60 + 30 * (len(TESTO_PROVA) + 1)
    img = Image.new("L", (larghezza, altezza), carta)
    d = ImageDraw.Draw(img)
    y = 30
    for riga in TESTO_PROVA:
        d.text((40, y), riga, font=font, fill=inchiostro)
        y += 30
    return img


def _degrada(
    img: Image.Image, sigma: float, rumore: float, gradi: float, seme: int = 7
) -> Image.Image:
    """Applica un degrado **noto**, per vedere se le stime lo ritrovano."""
    out = img
    if gradi:
        out = out.rotate(-gradi, resample=Image.BICUBIC, fillcolor=255)
    if sigma > 0:
        out = out.filter(ImageFilter.GaussianBlur(sigma))
    a = np.asarray(out).astype(np.float32)
    if rumore > 0:
        rng = np.random.default_rng(seme)
        a = a + rng.normal(0.0, rumore, a.shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _trova_font() -> str:
    for c in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(c).exists():
            return c
    raise SystemExit(
        "ERRORE: nessun font TrueType trovato. Serve per costruire le pagine "
        "dell'autoprova: senza, le stime non si possono validare."
    )


def autoprova() -> tuple[bool, list[tuple[float, float]]]:
    """Le stime sanno ritrovare valori noti?

    Restituisce (esito, taratura) dove `taratura` e' la corrispondenza
    misurata fra sigma di sfocatura e acutanza — quella che permette di
    leggere l'acutanza del corpus vero come una sfocatura.
    """
    font = _trova_font()
    pulita = _pagina_sintetica(font)
    problemi: list[str] = []

    print("  autoprova — le stime ritrovano valori noti?")

    # -- rumore -------------------------------------------------------
    # Su carta lontana dai due estremi: a 255 pieno il tetto tosa il rumore
    # e si finirebbe per pretendere un valore che nell'immagine non c'e'.
    grigia = _pagina_sintetica(font, carta=200, inchiostro=40)
    print("    rumore     noto  stimato   (carta a 200, non tosata dal tetto)")
    for atteso in (0.0, 6.0, 14.0, 24.0):
        m = misura(_degrada(grigia, 0.0, atteso, 0.0))
        scarto = abs(m.rumore - atteso)
        ok = scarto <= max(1.5, atteso * 0.15)
        print(f"      {atteso:6.1f}  {m.rumore:7.2f}   {'ok' if ok else 'NO'}")
        if not ok:
            problemi.append(f"rumore {atteso}: stimato {m.rumore:.2f}")

    # -- inclinazione -------------------------------------------------
    print("    inclinazione  nota  stimata")
    for atteso in (0.0, 0.6, -1.4, 2.2):
        m = misura(_degrada(pulita, 0.6, 4.0, atteso))
        scarto = abs(m.inclinazione - atteso)
        ok = scarto <= 0.35
        print(f"      {atteso:6.2f}  {m.inclinazione:7.2f}   {'ok' if ok else 'NO'}")
        if not ok:
            problemi.append(f"inclinazione {atteso}: stimata {m.inclinazione:.2f}")

    # -- sfocatura: taratura, non verifica ----------------------------
    # L'acutanza non e' un sigma. Qui si costruisce la corrispondenza fra i
    # due su pagine a sfocatura nota, e si pretende che sia MONOTONA: se
    # sfocando di piu' l'acutanza non scende, non misura la sfocatura.
    print("    sfocatura  nota  acutanza (dev'essere monotona decrescente)")
    taratura: list[tuple[float, float]] = []
    for sigma in (0.0, 0.5, 0.8, 1.3, 2.0, 2.6, 3.5):
        m = misura(_degrada(pulita, sigma, 8.0, 0.0))
        taratura.append((sigma, m.acutanza))
        print(f"      {sigma:6.2f}  {m.acutanza:8.4f}")
    acut = [a for _, a in taratura]
    monotona = all(b < a + 1e-4 for a, b in zip(acut, acut[1:]))
    if not monotona:
        problemi.append("l'acutanza non scende monotonamente con la sfocatura")
    print(f"      monotona: {'si' if monotona else 'NO'}")

    if problemi:
        print("\n  AUTOPROVA FALLITA:", file=sys.stderr)
        for p in problemi:
            print(f"    - {p}", file=sys.stderr)
        return False, taratura
    print("  autoprova superata\n")
    return True, taratura


def sigma_da_acutanza(acutanza: float, taratura: list[tuple[float, float]]) -> float:
    """Legge l'acutanza misurata come una sfocatura, usando la taratura.

    Interpolazione lineare fra i due punti di taratura che la racchiudono.
    Fuori dall'intervallo si restituisce l'estremo: estrapolare una curva
    tarata su sette punti sarebbe inventare.
    """
    if not np.isfinite(acutanza):
        return float("nan")
    coppie = sorted(taratura, key=lambda t: t[1])  # acutanza crescente
    if acutanza <= coppie[0][1]:
        return coppie[0][0]
    if acutanza >= coppie[-1][1]:
        return coppie[-1][0]
    for (s0, a0), (s1, a1) in zip(coppie, coppie[1:]):
        if a0 <= acutanza <= a1:
            if a1 - a0 < 1e-9:
                return s0
            t = (acutanza - a0) / (a1 - a0)
            return s0 + t * (s1 - s0)
    return float("nan")


# ------------------------------------------------------------------ main

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Misura il degrado di scansioni reali, per tarare il banco"
    )
    ap.add_argument("--corpus", type=Path, default=CORPUS_PREDEFINITO)
    ap.add_argument("--quante", type=int, default=0, help="limita le pagine (0 = tutte)")
    args = ap.parse_args(argv)

    ok, taratura = autoprova()
    if not ok:
        print(
            "Le stime non ritrovano valori noti: non si misura niente.",
            file=sys.stderr,
        )
        return 1

    pagine = sorted(
        p
        for p in args.corpus.rglob("*")
        if p.suffix.lower() in (".png", ".tif", ".tiff", ".jpg", ".jpeg")
    )
    if not pagine:
        print(
            f"ERRORE: nessuna immagine in {args.corpus}.\n"
            "  Il corpus non sta nel repository: licenza di sola ricerca e\n"
            "  documenti di persone reali. Va scaricato a parte (FUNSD:\n"
            "  https://guillaumejaume.github.io/FUNSD/) e scompattato li'.",
            file=sys.stderr,
        )
        return 1
    if args.quante:
        pagine = pagine[: args.quante]

    print(f"  corpus: {len(pagine)} pagine da {args.corpus}")
    misure: list[Misura] = []
    for i, p in enumerate(pagine, 1):
        try:
            misure.append(misura(Image.open(p)))
        except Exception as e:  # una pagina illeggibile non ferma la misura
            print(f"    saltata {p.name}: {e}", file=sys.stderr)
        if i % 50 == 0:
            print(f"    {i}/{len(pagine)}")

    if not misure:
        print("ERRORE: nessuna pagina misurabile", file=sys.stderr)
        return 1

    def riassunto(nome: str, valori: list[float], forma: str = "{:.2f}") -> None:
        v = sorted(x for x in valori if np.isfinite(x))
        if not v:
            print(f"    {nome:16s} nessun valore finito")
            return
        q = lambda f: v[min(len(v) - 1, int(f * len(v)))]  # noqa: E731
        print(
            f"    {nome:16s} mediana {forma.format(statistics.median(v))}"
            f"   q10 {forma.format(q(0.10))}   q90 {forma.format(q(0.90))}"
        )

    print(f"\n  MISURATO SU {len(misure)} SCANSIONI REALI\n")
    riassunto("livello carta", [m.livello_carta for m in misure])
    riassunto("livello inchio.", [m.livello_inchiostro for m in misure])
    riassunto("contrasto", [m.contrasto for m in misure], "{:.3f}")
    riassunto("rumore", [m.rumore for m in misure])
    riassunto("acutanza", [m.acutanza for m in misure], "{:.4f}")
    riassunto("inclinazione", [abs(m.inclinazione) for m in misure])

    sigmi = [sigma_da_acutanza(m.acutanza, taratura) for m in misure]
    riassunto("sfocatura equiv.", sigmi)

    print(
        "\n  ATTENZIONE, e va detto perche' cambia cosa si puo' concludere:\n"
        "  le pagine di FUNSD sono state RICAMPIONATE (altezza normalizzata a\n"
        "  1000 px). Il ricampionamento e' esso stesso un filtro: rumore e\n"
        "  sfocatura misurati qui sono quelli della pagina COSI' COME VIENE\n"
        "  CONSEGNATA, non quelli del sensore che l'ha acquisita. Restano\n"
        "  fedeli i livelli di carta e inchiostro, il contrasto e\n"
        "  l'inclinazione, che il ricampionamento non altera."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
