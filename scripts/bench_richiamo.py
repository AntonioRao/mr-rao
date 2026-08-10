"""Quanto ci sfugge: il banco del **richiamo**.

La meta' che non misuravamo
---------------------------

Tutti gli altri banchi di questo progetto misurano i **falsi positivi**:
quante volte il motore sbaglia su documenti che non contengono niente. E'
la meta' giusta da misurare per prima, perche' uno strumento che cancella
mezzo documento viene disinstallato — ed e' meta'.

L'altra meta' e' quella che conta per chi si fida: **quanti dati veri
restano nel documento**. Fino alla 1.20.0 non avevamo un numero.

Cosa rende questo corpus utilizzabile, e Ai4Privacy no
-------------------------------------------------------

Il primo tentativo e' stato con `ai4privacy`, ed e' fallito per una ragione
che vale la pena ricordare: **i valori non passano i conti**. Delle 51 carte
di credito nelle righe italiane ne passano 3 il controllo di Luhn, di IBAN
non ce n'e' nessuno, i telefoni hanno prefissi internazionali inesistenti.
Un richiamo misurato li' darebbe numeri bassissimi e falsi, perche' il
motore rifiuta quei valori **giustamente**.

Qui i conti tornano tutti, e non sulla parola di chi ha generato i dati: il
corpus porta un campo `checksum_ok`, e questo banco **non lo guarda**. Prima
di misurare qualunque cosa ricalcola Luhn, mod-97, il carattere di controllo
del codice fiscale e quello della partita IVA con le nostre funzioni. Se un
valore non passa, esce dalla misura: chiedere al motore di trovare un codice
sbagliato vorrebbe dire misurare la sua obbedienza, non il suo richiamo.

Cosa questo banco NON dice, e va letto prima dei numeri
-------------------------------------------------------

**Il corpus e' sintetico.** I testi nascono da modelli riempiti con valori
generati. Per gli identificatori con un conto dietro e' il suo punto di
forza — la forma e' quella vera e l'aritmetica pure. Per i **nomi** no, e la
ragione e' scomoda: i nomi generati vengono da elenchi, e i nostri
riconoscitori usano elenchi. Se i due elenchi si somigliano, il numero e'
alto per costruzione; se divergono, e' basso per costruzione. **Il richiamo
sui nomi va letto come indicativo, non come misura.**

Quello che invece resta valido sui nomi, ed e' la parte utile, sono i
**valori persi**: `Tommaso Gentile` e `Silvia Conti` non sfuggono per via di
un elenco, ma perche' «Gentile» apre una lettera e «Conti» sono i conti. Un
nome perso per quel motivo lo sarebbe anche in un documento vero.

I tre esiti
-----------

Per ogni valore atteso, uno solo:

* **redatto** — sparito dal testo. E' il richiamo;
* **segnalato** — rimasto, ma il rapporto lo elenca fra i sospetti. Non e'
  una vittoria e non e' una sconfitta: il documento non e' pulito, ma chi lo
  rilegge sa dove guardare;
* **perso in silenzio** — rimasto, e nessuno lo dice. **E' l'unico numero
  che conta davvero**, ed e' quello su cui va la soglia.

Uso
---

    venv\\Scripts\\python scripts\\bench_richiamo.py --corpus CARTELLA
    venv\\Scripts\\python scripts\\bench_richiamo.py --corpus CARTELLA --rigenera
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import (  # noqa: E402
    PrivacyOptions,
    _mask,
    apply_privacy_filter,
    cf_check_char_ok,
    iban_checksum_ok,
    luhn_ok,
    piva_check_ok,
)

ATTESO = RADICE / "tests" / "dati" / "richiamo_atteso.json"
NOME_CORPUS = "legale-it.jsonl"

# Etichetta del corpus -> (categoria nostra, conto indipendente da superare).
#
# Il conto e' `None` dove non ce n'e' uno: per gli indirizzi di posta la
# forma **e'** la validita', e un telefono italiano non ha cifre di
# controllo. Dove invece un conto esiste, si esegue -- e non si guarda il
# campo `checksum_ok` del corpus, che e' un'opinione di chi ha generato i
# dati. Misurare il nostro motore fidandosi dell'etichetta di un altro
# sarebbe una catena di due opinioni.
MAPPATURA = {
    "CF": ("codice_fiscale", cf_check_char_ok),
    "IBAN": ("iban", iban_checksum_ok),
    "PIVA": ("partita_iva", piva_check_ok),
    "CREDITCARDNUMBER": ("cards", luhn_ok),
    "EMAIL": ("emails", None),
    "PEC": ("emails", None),
    "TELEPHONENUM": ("phones", None),
    "FULLNAME": ("names", None),
}

# Etichette che il corpus ha e che questo banco **non** misura, col perche'.
# Sta qui e viene stampato: un elenco di esclusioni che nessuno legge e' un
# elenco che cresce da solo, e ogni riga che ci finisce e' una parte di
# documento su cui smettiamo di sapere qualcosa.
FUORI = {
    "CITY": "dentro `addresses`, non separabile senza cambiare la definizione",
    "STREET": "idem",
    "BUILDINGNUM": "idem",
    "ZIPCODE": "idem",
    "PROVINCE": "idem",
    "DATE": "le date si tolgono solo accanto a un contesto di nascita",
    "TIME": "non e' una categoria che trattiamo",
    "AGE": "non e' una categoria che trattiamo",
    "GENDER": "non e' una categoria che trattiamo",
    "ORG": "ragione sociale: non ce l'abbiamo (voce P6.4)",
    "TARGA": "non ce l'abbiamo (voce P6.4)",
    "CATASTO": "non ce l'abbiamo (voce P6.4)",
    "DOCID": "identificativo d'atto: non ce l'abbiamo (voce P6.4)",
    "RG": "idem",
    "CONTO": "coordinate non-IBAN: il corpus stesso le dichiara quasi tutte "
            "senza checksum valido",
    "ID_DOC": "forme di documento che non copriamo tutte (voce P6.4)",
    "IDCARDNUM": "idem",
    "DRIVERLICENSENUM": "la patente la copriamo, ma il corpus la mescola a "
                        "forme straniere: misura ibrida",
    "GIVENNAME": "meta' nome: la nostra unita' e' la persona intera",
    "SURNAME": "idem",
    "ATTORE": "ruolo processuale, non un identificatore",
    "CONVENUTO": "idem",
    "AVVOCATO": "idem",
    "GIUDICE": "idem",
    "TESTIMONE": "idem",
}

# Il richiamo sui nomi si misura ma non fa fallire il banco: vedi la
# docstring. Il numero resta stampato e congelato, perche' un crollo va
# visto -- semplicemente non e' lui a dire se il motore va bene.
INDICATIVE = {"names"}


def leggi(corpus: Path) -> list[dict]:
    sorgente = corpus / NOME_CORPUS
    if not sorgente.exists():
        raise SystemExit(
            f"manca {sorgente}: esegui prima scripts/scarica_corpus_legale_it.py"
        )
    return [
        json.loads(r)
        for r in sorgente.read_text(encoding="utf-8").splitlines()
        if r.strip()
    ]


def misura(righe: list[dict]) -> tuple[dict, dict, dict]:
    opzioni = PrivacyOptions()
    esiti: collections.Counter = collections.Counter()
    scartati: collections.Counter = collections.Counter()
    esempi: dict[str, list[str]] = collections.defaultdict(list)

    for riga in righe:
        entita = [e for e in riga["entities"] if e["label"] in MAPPATURA]
        if not entita:
            continue
        fuori, rapporto = apply_privacy_filter(riga["source_text"], opzioni)
        sospetti = {s.get("sample") for s in rapporto.to_dict()["suspects"]}
        for e in entita:
            categoria, conto = MAPPATURA[e["label"]]
            valore = e["value"]
            # Il conto viene prima di tutto: un valore che non lo supera non
            # e' un dato che il motore *avrebbe dovuto* trovare.
            if conto is not None and not _passa(conto, valore):
                scartati[categoria] += 1
                continue
            if valore not in fuori:
                esiti[(categoria, "redatto")] += 1
            elif _mask(valore) in sospetti:
                esiti[(categoria, "segnalato")] += 1
            else:
                esiti[(categoria, "perso")] += 1
                if len(esempi[categoria]) < 8:
                    esempi[categoria].append(valore)
    return esiti, scartati, esempi


def _passa(conto, valore: str) -> bool:
    try:
        return bool(conto(valore))
    except Exception:  # noqa: BLE001 - un valore storto non ferma il banco
        return False


def stampa(esiti, scartati, esempi, righe) -> dict:
    print(f"{len(righe)} documenti\n")
    print(f"{'categoria':18}{'redatti':>9}{'segnal.':>9}{'PERSI':>8}{'richiamo':>10}   ")
    misurato: dict[str, dict[str, int]] = {}
    for categoria in sorted({c for c, _ in esiti}):
        r = esiti[(categoria, "redatto")]
        s = esiti[(categoria, "segnalato")]
        p = esiti[(categoria, "perso")]
        totale = r + s + p
        nota = "  (indicativo)" if categoria in INDICATIVE else ""
        print(
            f"{categoria:18}{r:>9}{s:>9}{p:>8}{100 * r / totale:>9.1f}%{nota}"
        )
        for v in esempi.get(categoria, [])[:4]:
            print(f"      perso in silenzio: {v!r}")
        misurato[categoria] = {"redatto": r, "segnalato": s, "perso": p}

    if scartati:
        print("\nValori esclusi perche' non superano il conto (non sono un "
              "richiamo mancato):")
        for c, n in sorted(scartati.items()):
            print(f"   {c:18} {n}")

    print("\nEtichette del corpus NON misurate, e perche':")
    for e, perche in sorted(FUORI.items()):
        print(f"   {e:18} {perche}")
    return misurato


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True, type=Path)
    p.add_argument("--rigenera", action="store_true")
    a = p.parse_args()

    righe = leggi(a.corpus)
    esiti, scartati, esempi = misura(righe)
    misurato = stampa(esiti, scartati, esempi, righe)

    if a.rigenera:
        ATTESO.parent.mkdir(parents=True, exist_ok=True)
        ATTESO.write_text(
            json.dumps(
                {"documenti": len(righe), "categorie": misurato},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"\natteso riscritto in {ATTESO}")
        return 0

    if not ATTESO.exists():
        print("\nnessun atteso congelato: esegui con --rigenera dopo aver "
              "letto i numeri qui sopra")
        return 1

    atteso = json.loads(ATTESO.read_text(encoding="utf-8"))
    guasti: list[str] = []
    if atteso["documenti"] != len(righe):
        guasti.append(
            f"corpus diverso: {len(righe)} documenti, attesi {atteso['documenti']}"
        )
    for categoria, conti in atteso["categorie"].items():
        ora = misurato.get(categoria)
        if ora is None:
            guasti.append(f"{categoria}: non misurata piu'")
            continue
        # La soglia sta sui **persi in silenzio**, non sui redatti: un
        # valore che passa da «redatto» a «segnalato» e' un peggioramento
        # da guardare, ma non e' una fuga. Uno che passa a «perso» si'.
        if ora["perso"] > conti["perso"]:
            guasti.append(
                f"{categoria}: persi in silenzio {ora['perso']}, "
                f"erano {conti['perso']}"
            )
    if guasti:
        print("\nGUASTI:")
        for g in guasti:
            print(f"   {g}")
        return 1
    print("\nnessun peggioramento rispetto all'atteso congelato")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
