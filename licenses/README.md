# Licenze di terze parti (bundle)

Questa cartella accompagna Mr. Rao per **trasparenza** e per gli obblighi di
redistribuzione delle librerie open source.

| Percorso | Contenuto |
|----------|-----------|
| `pystray/COPYING.LGPL` | GNU **LGPL-3.0** (testo fornito con pystray) |
| `pystray/COPYING` | GNU **GPL-3.0** (richiamato dalla LGPL) |
| `pystray/LGPL-3.0.txt` | Copia ufficiale gnu.org (LGPL) |
| `pystray/GPL-3.0.txt` | Copia ufficiale gnu.org (GPL) |
| `pystray/NOTICE.txt` | Copyright e come ottenere/sostituire pystray |
| `../LICENSE` | Licenza del **codice Mr. Rao** |
| `../THIRD_PARTY.md` | Elenco dipendenze e link |

Il pacchetto contiene **una** libreria LGPL: pystray, per l'icona nella barra
di sistema. L'elenco completo delle dipendenze si **genera** dai pacchetti
realmente installati con `scripts/gen_third_party.py`, così non può divergere
da ciò che viene effettivamente distribuito.

## pystray (LGPL-3.0)

Mr. Rao **usa** [pystray](https://github.com/moses-palmer/pystray)
(Copyright © 2016–2022 Moses Palmér) per l’icona di system tray.

Conformità LGPL (in sintesi, non parere legale):

1. **Notice** — vedi `pystray/NOTICE.txt` e la UI (ⓘ).  
2. **Testo della licenza** — file in questa cartella.  
3. **Sorgente** — https://github.com/moses-palmer/pystray (e PyPI `pystray`).  
4. **Sostituzione della libreria** — Mr. Rao importa `pystray` come modulo Python
   standard; puoi installare un’altra versione o un fork compatibile nell’ambiente
   Python / nel bundle (vedi `docs/LGPL_PYSTRAY.md`).  
5. **Nessuna restrizione aggiuntiva su pystray.** Mr. Rao è distribuito sotto
   AGPL-3.0, compatibile con la LGPL: distribuendo il sorgente, l'obbligo di
   consentire la sostituzione della libreria è soddisfatto di conseguenza.

## PyInstaller (GPLv2 con eccezione)

Usato solo per **costruire** il pacchetto portable. La sua eccezione consente
esplicitamente di distribuire programmi non liberi costruiti con esso: è ciò
che rende lecita la distribuzione di `MrRao.exe`, il cui bootloader ne deriva.

---

Se distribuisci un portable PyInstaller, **copia l’intera cartella `licenses/`**
accanto all’applicazione (lo fa `scripts/build_portable.bat`).
