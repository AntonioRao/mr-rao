# Mr. Rao su macOS (Apple Silicon)

Pacchetto per **Mac con chip Apple** (M1, M2, M3, M4). Provato sulla
configurazione di riferimento: **MacBook Air M1 2020, 8 GB, macOS Tahoe
26.5.2**. Non gira sui Mac Intel.

Non è notarizzato. La notarizzazione di Apple costa **99 USD/anno**
(Apple Developer Program) e **non esiste un equivalente gratuito**.
È la stessa scelta già fatta su Windows: niente certificato a pagamento,
firma verificabile con Sigstore quando il file esce da GitHub Actions.

## Cosa puoi fare senza pagare

| Cosa | Costo | Cosa vede chi apre il file |
|---|---|---|
| **Firma ad-hoc** (`codesign -s -`) | 0 | Il kernel accetta il binario. Finder **non** mostra un nome: identità vuota. Gatekeeper avvisa |
| **Sigstore / GitHub Attestations** | 0 | Come l’`.exe` Windows: `gh attestation verify` dice da quale commit è uscito. **Non** è quello che legge Gatekeeper |
| Developer ID Apple + notarizzazione | 99 USD/anno | Unico modo per far comparire «Antonio Andrea Rao» in Finder e togliere l’avviso |

Senza la firma ad-hoc un `.app` arm64 **non parte**: lo uccide il kernel,
non Gatekeeper. Con la firma ad-hoc parte, dopo un gesto esplicito.

Non si può scrivere il nome a mano nella firma ad-hoc: Apple accetta solo un
certificato **Developer ID Application** emesso da loro. SignPath (la
domanda già inviata) firma Authenticode per **Windows**, non sostituisce
Apple su Mac. Inventare un’identità senza quel certificato sarebbe una
firma falsa, peggio del vuoto.

## Primo avvio (Sequoia, Tahoe e successivi)

1. Scarica `MrRao-macos-arm64.dmg` e aprilo. macOS chiede conferma sul disco:
   **Apri comunque**.
2. Trascina **Mr. Rao** su **Applicazioni**. Falla davvero, prima di
   proseguire: dal disco montato l'app resta in sola lettura e il passo 4 non
   trova niente da sbloccare.
3. Doppio clic su Mr. Rao in Applicazioni. **Verrà bloccata**, con un avviso
   che ha il solo pulsante *Fine*. È previsto: serve a dire a macOS quale app
   stai per autorizzare.
4. **Impostazioni di Sistema → Privacy e sicurezza**, in fondo alla sezione
   *Sicurezza*: compare «Mr. Rao è stata bloccata» con il pulsante **Apri
   comunque**. Premilo, autentica, e al dialogo che segue scegli **Apri**.
5. Il programma ascolta su `127.0.0.1` e apre la finestra (o il browser).
   La scorciatoia appunti **Ctrl+Alt+R non c'è**: è Windows-only.

Da qui in poi si apre con un doppio clic come qualunque altra app.

Chi preferisce il Terminale fa in una riga quello che i passi 3 e 4 fanno a
mano — toglie la marcatura di «scaricato da internet»:

```bash
xattr -dr com.apple.quarantine "/Applications/Mr. Rao.app"
```

> **Il «tasto destro → Apri» non funziona più.** Era la via classica, ed è
> quella che questa pagina consigliava fino alla 1.27.1. Apple **l'ha tolta
> con macOS 15 Sequoia**: da lì in avanti il menu contestuale non offre più
> l'eccezione, e l'unica strada è Impostazioni di Sistema. Su Tahoe (26) è
> ancora così. L'istruzione vecchia non era pericolosa, era peggio: mandava
> l'utente a cercare un comando che non esiste, e sembrava che l'app fosse
> rotta.

Non è un buco: è lo stesso avviso «editore sconosciuto» di Windows, detto
nel linguaggio di Apple.

## Come si costruisce

Su un Mac M1/M2/… (meglio non sul portatile da 8 GB: PyInstaller pesa):

```bash
chmod +x scripts/build_mac.sh
./scripts/build_mac.sh
```

Esce `dist/MrRao-macos-arm64.dmg` (disco con l’app e il collegamento ad
Applicazioni). Niente zip da scompattare. La CI monta quel disco e rilancia
`verify_build` sull’eseguibile *dentro* (`scripts/verify_dmg.sh`): si prova
il file che si condivide, non solo l’`.app` prima di impacchettarlo.

Da Windows / senza Mac: Actions → workflow **macOS** → Run workflow.
Su un tag `v*` gira da solo. Il file da condividere è sulla release,
non l’artefatto Actions.

Verificare la provenienza (dopo un upload da Actions):

```bash
gh attestation verify MrRao-macos-arm64.dmg --repo AntonioRao/mr-rao
```

## Cosa non è in questo v1

* Binario Intel / universale
* `.dmg` con freccia verso Applicazioni (lo zip col `.app` basta)
* Quick Action / tasto destro del Finder (la CLI `mr_rao.cli` da Terminale
  c’è)
* Scorciatoia globale sugli appunti
* Notarizzazione

Le istruzioni della bozza in `Builds/mrrao-piano-build-mac.md` restano
valide sulla strategia (PyInstaller, niente Tauri). Due correzioni già
applicate qui: firma **senza** `--deep`, scorciatoia appunti **spenta**
fuori da Windows.
