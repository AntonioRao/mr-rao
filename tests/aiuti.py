"""Attrezzi condivisi dai test. Non contiene test.

Perche' esiste
--------------

Dalla 1.20.0 i segnaposto sono **numerati di default**: l'uscita porta
`{{PHONE_1}}`, non `{{PHONE}}`. La maggior parte dei test di questo
progetto misura **quale riconoscitore ha morso**, non come sono scritti i
segnaposto, e la numerazione romperebbe quelle asserzioni in due modi
diversi -- uno rumoroso e uno silenzioso:

* le positive (`"{{PHONE}}" in fuori`) diventano rosse, e si vede;
* le negative (`"{{PHONE}}" not in fuori`) diventano **vere sempre**,
  perche' nel testo c'e' `{{PHONE_1}}`. Sono ventitre' nella suite, e
  sarebbero diventate ventitre' controlli che non possono piu' fallire --
  verdi, e senza guardare piu' niente.

Il secondo modo e' quello che conta, ed e' il motivo per cui qui si
appiattisce invece di riscrivere le asserzioni una per una: appiattendo,
positive e negative tornano a voler dire esattamente quello che dicono.

Dove la numerazione viene misurata sul serio
---------------------------------------------

In `tests/test_segnaposto_numerati.py`, che non appiattisce niente e
chiama il motore con i suoi valori predefiniti. Se qualcuno cancellasse
quel file, la numerazione resterebbe **non provata da nessuna parte** pur
essendo accesa in produzione: e' l'unico rischio che questo modulo
introduce, e sta scritto qui perche' si veda.
"""

from __future__ import annotations

from mr_rao.privacy import apply_privacy_filter as _motore
from mr_rao.privacy import senza_numeri

__all__ = ["apply_privacy_filter"]


def apply_privacy_filter(testo, options=None):
    """Il motore vero, con i numeri dei segnaposto appiattiti.

    Stessa firma e stesso valore di ritorno di
    `mr_rao.privacy.apply_privacy_filter`: cambia solo la forma dei
    segnaposto nel testo. Il rapporto non viene toccato -- i conteggi e i
    sospetti sono gli stessi.
    """
    fuori, rapporto = _motore(testo, options)
    return senza_numeri(fuori), rapporto
