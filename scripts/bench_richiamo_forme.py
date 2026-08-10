"""Il banco che misura quello che **perdiamo**, sui dati che hanno una forma.

Perche' esiste
--------------

Tutti gli altri banchi di questo progetto misurano i falsi positivi: quante
volte il motore sbaglia su documenti che non contengono niente. E' la meta'
giusta da misurare per prima, ed e' meta'.

`bench_corpus_pubblico.py` guarda l'altra meta' sulle Gazzette Ufficiali, ma
li' l'atteso e' un numero congelato: dice se il richiamo **scende**, non
quanto vale. Questo banco lo misura, su un corpus etichettato da altri --
dove per ogni dato c'e' scritto dove comincia, dove finisce e cosa e'.

Su cosa si puo' misurare, e su cosa no
--------------------------------------

Il corpus (`ai4privacy`, righe italiane) e' **tradotto a macchina e
sintetico**. Questo lo rende inutile per i nomi e le date, e utilizzabile
per i dati la cui forma non dipende dalla lingua. Ma non basta dirlo: prima
di misurare, ogni valore va guardato.

Misurato sul campione, ed e' il motivo per cui questo banco e' fatto cosi':

* **carte**: 3 valori su 51 passano Luhn. Sono numeri inventati, e il motore
  li rifiuta **giustamente**. Un richiamo calcolato su tutti darebbe il 6% e
  sarebbe un numero falso -- non una perdita, ma l'aritmetica che funziona;
* **IBAN**: l'etichetta **non esiste** nel corpus italiano. Zero casi;
* **telefoni**: quasi tutti con prefissi internazionali inesistenti (`+871`,
  `+75`, `+83`). Anche qui il motore li scarta per il motivo giusto;
* **email**: valori validi e domini veri. L'unica categoria pulita.

Quindi il corpus si divide in due, e servono entrambe le meta':

    valori che superano un conto INDIPENDENTE  ->  misurano il RICHIAMO
    valori che non lo superano                 ->  misurano i FALSI POSITIVI

La seconda meta' e' un regalo: 48 numeri di carta non-Luhn dentro frasi
italiane sono un banco di falsi positivi che non avevamo.

Il criterio dell'atteso non viene dal nostro motore
---------------------------------------------------

**E' la regola che rende questo banco una verifica invece che una
tautologia.** Se per decidere quali telefoni «dovrebbero» essere trovati
usassi `_phone_is_plausible`, misurerei il motore con il motore: il
risultato sarebbe 100% per costruzione, sempre, anche a motore rotto.

Quindi:

* **carte** -> Luhn, che e' uno standard, non nostro codice;
* **telefoni** -> il prefisso internazionale deve essere **assegnato**
  secondo la lista ITU-T E.164 scritta qui sotto a mano;
* **email** -> la forma `qualcosa@dominio.tld` con un TLD di almeno due
  lettere. Nessun giudizio nostro.

I tre esiti, come nel resto del progetto
----------------------------------------

Per ogni valore atteso: **redatto**, **segnalato** (compare fra i sospetti),
oppure **perso in silenzio**. Il terzo e' il numero che conta.

Uso
---

    venv\\Scripts\\python scripts\\bench_richiamo_forme.py --corpus CARTELLA
    venv\\Scripts\\python scripts\\bench_richiamo_forme.py --corpus CARTELLA --rigenera
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from mr_rao.privacy import PrivacyOptions, apply_privacy_filter  # noqa: E402

ATTESO = RADICE / "tests" / "dati" / "richiamo_forme_atteso.json"
NOME_CORPUS = "ai4privacy-it.jsonl"

# ---------------------------------------------------------------------------
# I criteri indipendenti
# ---------------------------------------------------------------------------

# Prefissi internazionali assegnati (ITU-T E.164). Scritti qui e non dedotti
# dal nostro motore: e' il punto in cui questo banco smette di essere una
# tautologia. L'elenco e' dei prefissi a una, due e tre cifre effettivamente
# in uso; quelli non assegnati -- +75, +83, +871 e compagnia -- restano
# fuori apposta, ed e' proprio quello che il corpus contiene di piu'.
PREFISSI_ASSEGNATI = {
    "1", "7", "20", "27", "30", "31", "32", "33", "34", "36", "39", "40", "41",
    "43", "44", "45", "46", "47", "48", "49", "51", "52", "53", "54", "55",
    "56", "57", "58", "60", "61", "62", "63", "64", "65", "66", "81", "82",
    "84", "86", "90", "91", "92", "93", "94", "95", "98", "211", "212", "213",
    "216", "218", "220", "221", "222", "223", "224", "225", "226", "227",
    "228", "229", "230", "231", "232", "233", "234", "235", "236", "237",
    "238", "239", "240", "241", "242", "243", "244", "245", "248", "249",
    "250", "251", "252", "253", "254", "255", "256", "257", "258", "260",
    "261", "262", "263", "264", "265", "266", "267", "268", "269", "290",
    "291", "297", "298", "299", "350", "351", "352", "353", "354", "355",
    "356", "357", "358", "359", "370", "371", "372", "373", "374", "375",
    "376", "377", "378", "380", "381", "382", "383", "385", "386", "387",
    "389", "420", "421", "423", "500", "501", "502", "503", "504", "505",
    "506", "507", "508", "509", "590", "591", "592", "593", "594", "595",
    "596", "597", "598", "599", "670", "672", "673", "674", "675", "676",
    "677", "678", "679", "680", "681", "682", "683", "685", "686", "687",
    "688", "689", "690", "691", "692", "850", "852", "853", "855", "856",
    "880", "886", "960", "961", "962", "963", "964", "965", "966", "967",
    "968", "970", "971", "972", "973", "974", "975", "976", "977", "992",
    "993", "994", "995", "996", "998",
}

RE_EMAIL_MINIMA = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)*\.[A-Za-z]{2,}$")


def luhn_indipendente(valore: str) -> bool:
    """Luhn scritto qui, non importato: e' uno standard, e serve che il
    criterio dell'atteso non passi da nessuna riga del motore."""
    cifre = [int(c) for c in valore if c.isdigit()]
    if len(cifre) < 12:
        return False
    somma = 0
    for i, c in enumerate(reversed(cifre)):
        if i % 2:
            c *= 2
            if c > 9:
                c -= 9
        somma += c
    return somma % 10 == 0


def prefisso_assegnato(valore: str) -> bool:
    """`+39 …`, `0039 …`: il prefisso esiste davvero secondo E.164?

    Un numero senza prefisso internazionale non si puo' giudicare da fuori
    -- «02 1234567» e' un fisso italiano o un codice qualsiasi -- quindi
    resta fuori dall'atteso invece di essere dato per buono.
    """
    t = valore.strip()
    if t.startswith("+"):
        resto = t[1:]
    elif t.startswith("00"):
        resto = t[2:]
    else:
        return False
    cifre = "".join(c for c in resto if c.isdigit())
    return any(cifre.startswith(p) for p in PREFISSI_ASSEGNATI if len(p) <= 3)


# etichetta del corpus -> (categoria nostra, criterio indipendente)
MAPPATURA = {
    "EMAIL": ("emails", lambda v: bool(RE_EMAIL_MINIMA.match(v.strip()))),
    "TELEPHONENUM": ("phones", prefisso_assegnato),
    "CREDITCARDNUMBER": ("cards", luhn_indipendente),
}

# Etichette che il corpus ha e che questo banco **non** misura, con il
# perche'. Sta qui e non in un commento perche' il banco lo stampa: un
# elenco di esclusioni che nessuno legge e' un elenco che cresce da solo.
FUORI = {
    "GIVENNAME": "nomi inventati e tradotti: misurerebbe i nostri elenchi, non il motore",
    "SURNAME": "idem",
    "DATE": "forme anglosassoni tradotte («luglio 4o, 2008»)",
    "TIME": "non e' una categoria che trattiamo",
    "AGE": "non e' una categoria che trattiamo",
    "SEX": "non e' una categoria che trattiamo",
    "GENDER": "non e' una categoria che trattiamo",
    "TITLE": "un appellativo non e' un identificatore",
    "CITY": "dentro `addresses`, non separabile senza cambiare la definizione",
    "STREET": "idem",
    "BUILDINGNUM": "idem",
    "ZIPCODE": "idem",
    "IDCARDNUM": "forme non italiane: il documento italiano ha un'altra faccia",
    "PASSPORTNUM": "idem",
    "DRIVERLICENSENUM": "idem",
    "SOCIALNUM": "codice statunitense in contesto italiano: caso ibrido",
    "TAXNUM": "non e' detto sia una partita IVA italiana",
}


def esito_di(valore: str, testo_redatto: str, sospetti: list[dict]) -> str:
    """redatto | segnalato | perso."""
    if valore not in testo_redatto:
        return "redatto"
    # Il campione dei sospetti e' mascherato dal motore: si confronta la
    # forma mascherata, non il valore.
    from mr_rao.privacy import _mask  # noqa: PLC0415

    atteso = _mask(valore)
    if any(s.get("sample") == atteso for s in sospetti):
        return "segnalato"
    return "perso"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", required=True, type=Path)
    p.add_argument("--rigenera", action="store_true")
    a = p.parse_args()

    sorgente = a.corpus / NOME_CORPUS
    if not sorgente.exists():
        print(f"manca {sorgente}: esegui prima scarica_corpus_ai4privacy.py", file=sys.stderr)
        return 2

    righe = [json.loads(r) for r in sorgente.read_text(encoding="utf-8").splitlines() if r.strip()]
    print(f"{len(righe)} righe italiane\n")

    conti: dict[str, dict[str, int]] = {}
    esempi: dict[str, list[str]] = {}
    for riga in righe:
        maschere = riga.get("privacy_mask") or []
        interessanti = [m for m in maschere if m["label"] in MAPPATURA]
        if not interessanti:
            continue
        testo, rapporto = apply_privacy_filter(riga["source_text"], PrivacyOptions())
        d = rapporto.to_dict()
        for m in interessanti:
            categoria, criterio = MAPPATURA[m["label"]]
            valido = criterio(m["value"])
            gruppo = f"{categoria}/{'valido' if valido else 'invalido'}"
            e = esito_di(m["value"], testo, d.get("suspects", []))
            conti.setdefault(gruppo, {}).setdefault(e, 0)
            conti[gruppo][e] += 1
            if e == "perso" and valido:
                esempi.setdefault(gruppo, []).append(m["value"])

    print("VALORI CHE SUPERANO UN CONTO INDIPENDENTE -> misurano il richiamo")
    guasti: list[str] = []
    for gruppo in sorted(g for g in conti if g.endswith("/valido")):
        c = conti[gruppo]
        tot = sum(c.values())
        persi = c.get("perso", 0)
        print(
            f"  {gruppo:18} {tot:5} casi | redatti {c.get('redatto', 0):5} "
            f"| segnalati {c.get('segnalato', 0):4} | PERSI {persi:4}"
        )
        for v in esempi.get(gruppo, [])[:3]:
            print(f"      perso: {v!r}")

    print("\nVALORI CHE NON LO SUPERANO -> misurano i falsi positivi (atteso: redatti ZERO)")
    for gruppo in sorted(g for g in conti if g.endswith("/invalido")):
        # I telefoni **non** stanno qui, e il motivo e' che il conto usato
        # per gli attesi non e' una prova di validita': dice solo «ha un
        # prefisso internazionale assegnato». Un numero senza prefisso --
        # «06 4455 6677» -- e' un telefono italiano validissimo, e redigerlo
        # e' la cosa giusta. Contarlo fra i falsi positivi darebbe un numero
        # alto e falso, che e' peggio di nessun numero.
        #
        # Per le carte il conto e' Luhn, che una prova lo e' davvero: 260
        # numeri di sedici cifre che non lo passano, dentro frasi italiane,
        # sono un banco di falsi positivi vero -- e il motore ne redige zero.
        if gruppo.startswith("phones/"):
            continue
        c = conti[gruppo]
        tot = sum(c.values())
        print(
            f"  {gruppo:18} {tot:5} casi | REDATTI {c.get('redatto', 0):5} "
            f"| segnalati {c.get('segnalato', 0):4} | ignorati {c.get('perso', 0):4}"
        )
    print("  phones             fuori: «senza prefisso internazionale» non vuol "
          "dire «non e' un telefono»")

    print("\nEtichette del corpus NON misurate, e perche':")
    for e, perche in sorted(FUORI.items()):
        print(f"  {e:18} {perche}")
    print("  IBAN               assente dal corpus italiano: zero casi")

    misurato = {g: dict(sorted(c.items())) for g, c in sorted(conti.items())}
    if a.rigenera:
        ATTESO.parent.mkdir(parents=True, exist_ok=True)
        ATTESO.write_text(
            json.dumps({"righe": len(righe), "gruppi": misurato}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        print(f"\natteso riscritto in {ATTESO}")
        return 0

    if not ATTESO.exists():
        print("\nnessun atteso congelato: esegui con --rigenera dopo aver letto i numeri")
        return 1

    atteso = json.loads(ATTESO.read_text(encoding="utf-8"))
    if atteso["righe"] != len(righe):
        guasti.append(f"corpus diverso ({len(righe)} righe, attese {atteso['righe']})")
    for gruppo, c in atteso["gruppi"].items():
        if misurato.get(gruppo) != c:
            guasti.append(f"{gruppo}: {misurato.get(gruppo)} invece di {c}")
    if guasti:
        print("\nGUASTI:")
        for g in guasti:
            print(f"  {g}")
        return 1
    print("\ntutto come atteso")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
