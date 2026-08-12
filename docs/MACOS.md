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

## Primo avvio (Tahoe e dintorni)

1. Scarica `MrRao-macos-arm64.dmg`, aprilo, trascina **Mr. Rao** su
   **Applicazioni**.
2. **Non** fare doppio clic la prima volta: tasto destro → **Apri** → Apri.
3. Se Tahoe lo blocca ancora: Impostazioni di Sistema → Privacy e
   sicurezza → **Apri comunque**.
4. Il programma ascolta su `127.0.0.1` e apre la finestra (o il browser).
   La scorciatoia appunti **Ctrl+Alt+R non c’è**: è Windows-only.

Non è un buco: è lo stesso avviso «editore sconosciuto» di Windows, detto
nel linguaggio di Apple.

## Come si costruisce

Su un Mac M1/M2/… (meglio non sul portatile da 8 GB: PyInstaller pesa):

```bash
chmod +x scripts/build_mac.sh
./scripts/build_mac.sh
```

Esce `dist/MrRao-macos-arm64.dmg` (disco con l’app e il collegamento ad
Applicazioni). Niente zip da scompattare.

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
