# Privacy — Mr. Rao

## Principi

1. **Tutto locale** — nessun invio a cloud  
2. **Font di sistema** — nessuna Google Fonts  
3. **Cronologia browser** solo in RAM  
4. **File temp** cancellati dopo la conversione  

## Filtri

| Tipo | Placeholder | Note |
|------|-------------|------|
| Email | `{{EMAIL}}` | Regex + Scrubadub |
| Telefoni | `{{PHONE}}` | IT `+39`, cellulari 3xx |
| CF | `{{CODICE_FISCALE}}` | Pattern 16 caratteri |
| IBAN | `{{IBAN}}` | Generico EU |
| P.IVA | `{{PARTITA_IVA}}` | Con contesto IT / keyword |
| Nomi IT | `{{NAME}}` | Liste nomi/cognomi comuni |
| Importi | `{{AMOUNT}}` | Opzionale |

## Report

La risposta API include `redaction: { total, counts }` e l’UI mostra un badge.

## Limiti

- I detector nomi non coprono tutti i cognomi italiani  
- Scrubadub è orientato all’inglese; i pattern custom compensano  
- Non sostituisce una valutazione DPIA / legale formale  
