# RESULT2 — mnemonic-proxy vs pi da solo, test 2: sessione lunga "salepren" (card t_4ea4c28c)

Data: 12/10/2026, AI395. Corse: B (pi da solo) 03:09–07:09, A (pi → mnemonic-proxy 0.3.2) 07:10–11:00.
n=1 per lato. Nessuna review LLM: tutti i voti vengono da test e regex scritti prima delle corse.

## Impianto

- Build ds4: `<ds4>/ds4-latest`, ramo `main-plus-qwen-rocm` 6bcd400 = upstream main fc80bd6 + 2 commit ROCm Qwen
  locali. **Il supporto ROCm per Qwen3.8 NON è ufficiale**: upstream fc80bd6 non avvia Qwen3.8 su ROCm.
- Modello: `<ds4>/ds4-qwen-rocm/gguf/Qwen3.8-Flash-Next-Q2.gguf`. Senza MTP, `--ctx 32768`, `-t 12`, `nice 19`,
  `ionice -c3`, `--kv-disk-dir <ds4>/long-kv2 --kv-disk-space-mb 12288`, KV svuotata prima di ogni corsa.
  Sono gli stessi flag della corsa A di t_cc27eaa0, a parte la cartella KV.
- Parametri visti nel trace di ds4, uguali in A e in B: temperature 1.0, top_p 1.0, min_p 0.05, seed 0,
  reasoning_effort medium, max_tokens 4096. ds4 non espone altro seme per richiesta.
- pi 1.0.3.
  - B (`pi-agent-direct`): contextWindow 32768, compattazione nativa con `reserveTokens 8192`,
    `keepRecentTokens 8000` (gli stessi valori di run-B di t_cc27eaa0).
  - A (`pi-agent-proxy`): compattazione di pi spenta, pi vede 131072. Il proxy legge 32768 da ds4 e
    scala le soglie ×0,25.
  - maxTokens 4096 in entrambe.
- Proxy: `mnemonic-proxy==0.3.2` (venv-proxy di long-run), con `config.ds4.json` del tag v0.3.2 e il
  tokenizer di Qwen3.8.
- Guardia: MemAvailable < 12 GB → stop. Non è mai scattata: il minimo è stato 48,8 GiB.
- Ordine B poi A, come chiesto. Mini-corsa M di 3 passi prima di partire (15 min, esclusa dai risultati).

## Il compito (congelato prima delle corse)

| file | sha256 |
|---|---|
| prompts.txt (29 passi) | c7241dbf8f27f301799f9490f27a13249e390b73184ebacf3d86a78565f397a9 |
| gen_data.py (seme 20261012) | 234c2551d146428923a435e670ca6891a984f4d09b54c7e926dc6f5cb01fa2f7 |
| hidden/tests/test_hidden.py (87 test) | 0b92eafe6b939965471f7cd22382ae990b580b3efe90ed607fef71111164b850 |
| hidden/answers.json (pre-corsa) | 7f07657fb9dc37e3fa6ff739a42dfda9180966ee213e7589493d96edb86b8e75 |

- Il compito è "salepren": un pacchetto Python per prenotare sale riunioni, solo stdlib, con CLI e test.
- 16 regole (R1–R16) date una volta sola in passi diversi. Tre vengono modificate più avanti:
  R3 al passo 11, R5 al 13, R6 al 19.
- Tre output grandi da leggere con `cat`, cancellati subito dopo: sale.csv 3,7K token, storico_2025.log 5,2K,
  segnalazioni_ottobre.log 5,6K.
- Sonde ai passi 8, 14, 20 e 28, di tipi misti: dato esatto, regola attuale, perché, elenco delle regole,
  preferenza, controllo.
- La suite nascosta sta in `<cache>/salepren-hidden`, fuori dall'albero della corsa. L'ho verificata così:
  - 87/87 sull'implementazione di riferimento;
  - 11 mutanti, ciascuno con una regola dimenticata o rimasta alla versione vecchia: ognuno fa fallire almeno un test;
  - grep sulle sessioni: l'agente non ha mai toccato né la suite né il riferimento.
- Una correzione del valutatore dopo le corse, dichiarata qui: nella sonda 20, domanda (5), ho aggiunto
  `chi ha fatt` alla regex dell'autore. A aveva scritto "solo chi ha fatto la prenotazione", che la regex
  originale non riconosceva. Il file pre-corsa resta salvato come `answers.pre-run.json`. Effetto: A passa da 4/6 a 5/6
  alla sonda 20. B non è toccata.
- Valutatore: `grade.py`, sha256 3c4477ff… Il testo di ogni passo viene preso da tutti i messaggi assistant
  della sessione di pi, perché `pi -p` stampa solo l'ultimo.

## Tabella A vs B (finale)

| misura | A (proxy) | B (pi da solo) |
|---|---|---|
| passi completati entro 4 h | **29/29** | 10/29 (timebox durante il passo 11) |
| durata s | 13825 | 14400 |
| richieste a ds4 | 87 | 154 |
| token letti tot | 361 893 | 510 514 |
| token letti p50 / p90 / max | 206 / 15 131 / 22 511 | 177 / 13 660 / 27 515 |
| richieste ≥ 4000 token letti | 24 | 37 |
| riletture da zero (ctx=0) | **1** | 38 |
| prefill totale s | 4447 | 6368 |
| TTFT server s media / p50 / p95 / max | 51,1 / 3,8 / 207 / 276 | 41,3 / 3,5 / 197 / 334 |
| prefill tok/s (≥1000 tok) / decode tok/s | 82,4 / 18,8 | 81,7 / 19,1 |
| finish length / tool_calls / stop | **26** / 57 / 4 | 8 / 120 / 26 |
| tempo nei turni finish=length | **8189 s** (67% del tempo richieste) | 2636 s (18%) |
| compattazioni pi (richieste di riassunto) | 0 | 10 compattazioni, 24 richieste di riassunto = **5717 s** (40%), 6 finite in length |
| mascheramenti / cambi segmento / recall proxy | 5 / 1 / 10 | — |
| MemAvailable min / GTT max GiB | 49,0 / 51,6 | 48,8 / 51,3 |
| intermedie passo 2 / passo 4 (conteggi) | sbagliata / sbagliata (risposta troncata, vuota) | giusta / giusta |
| sonda 8 | **6/6** | 5/6 (lotto: "non lo so") |
| sonda 14 | 6/6 | non eseguita |
| sonda 20 | 5/6 | non eseguita |
| sonda 28 (finale) | **0/8** (turno finito in length, nessun testo) | non eseguita |
| test nascosti, codice finale | **87/87** | 59/87 |
|   requisiti presto non modificati | 29/29 | 29/29 |
|   requisiti modificati (R3, R5, R6) | 22/22 | 11/22 |
|   requisiti tardi | 36/36 | 19/36 |
| DECISIONI.md / README.md | assenti | assenti (passi non raggiunti) |
| py_compile ko / import esterni | 0 / nessuno | 0 / nessuno |
| test propri dell'agente | 0 (cartella tests/ vuota) | 54, OK |
| riga «In breve:» (preferenza utente) | 4/29 | 7/11 |

Tipi di sonda (A; B ha risposto solo alla sonda 8):

| tipo | giuste A |
|---|---|
| dato esatto | 6/9 |
| perché | 2/4 |
| regola | 3/3 |
| regola attuale | 3/3 |
| preferenza | 1/2 |
| controllo | 2/4 |
| elenco regole | 0/1 |

Le risposte sbagliate di A vengono tutte dalla sonda 28, che è vuota, più la (6) della sonda 20.

## Confronto a parità di passo (istantanee di task/)

| passo | A test nascosti | B test nascosti |
|---|---|---|
| 8 | 0/87 (47 righe, scheletro del passo 1) | 50/87 (996 righe) |
| 10–11 | 0/87 | 59/87 (fine corsa B) |
| 14, 20, 25 | 0/87 | — |
| 26 | **87/87** (679 righe, 7 file) | — |

**A parità di passo, B è molto avanti sul codice.** A non scrive codice dal passo 2 al passo 25. Al passo 26
("refactoring finale") riscrive tutto il pacchetto in una volta, a memoria, e da lì passa tutti i test nascosti.

## A: il problema di qualità (diagnosi con evidenze)

Che cosa è successo:
- A ha 26 turni finiti con finish=length, quasi tutti con gen=4096. I passi 2–7, 9–13, 15–19 e 21–29 hanno
  tutti almeno un turno così.
- Ognuno di quei turni è fatto solo di ragionamento: 10–20K caratteri di thinking, nessuna tool call,
  nessun testo.
- Il codice resta lo scheletro del passo 1 fino al passo 25.
- Al passo 26 compare un pacchetto in `salpren/` (nome sbagliato), dopo che l'agente ha cancellato
  `salepren/` con `rm -rf`. Nello stesso passo lo rinomina con `mv salpren salepren`. Il codice finale
  quindi sta in `salepren/`, e il voto ufficiale 87/87 è sul nome giusto. Il voto separato su `salpren/`
  chiesto nella nota del controller non serve: a fine corsa `salpren/` non esiste più.
- B ha avuto un turno così al passo 3 (8686 caratteri) e uno al passo 5, e si è ripresa subito.

1. **La tool call troncata del passo 2 non arriva al modello.** pi salva il turno con `stopReason=length` come
   blocchi `thinking` e/o `text`, senza tool call. È così in A e in B (sessioni pi). Nel trace di ds4 non c'è
   nessun messaggio assistant con tool_calls troncate né con contenuto vuoto: `vuoti=0` in tutte le 87
   richieste di A (`run-A/diag.txt`). Le "invalid tool call returned as assistant text" (A 8, B 4) ds4 le
   restituisce come testo, e pi le tratta come testo in tutti e due i casi.
2. **Il proxy non toglie il ragionamento.** Nell'ultima richiesta inoltrata, tutti i 28 messaggi assistant di A
   hanno `reasoning_content` (B: 14 su 14). Il proxy maschera solo output di tool, con il segnaposto
   `⟪ctx-archive id=…⟫`: 5 mascheramenti, prima volta alle 07:53. Le differenze nel numero di messaggi tra pi e
   ds4 compaiono solo dopo il cambio di segmento delle 10:20.
3. **Che cosa cambia davvero tra A e B nella richiesta.** I turni troncati che pi salva senza tool call
   lasciano messaggi user consecutivi. B, con la compattazione, ne ha al massimo 1 per richiesta. A ne arriva
   a 13 in 17 richieste (`user_consecutivi=13`), cioè fino a 13 richieste dell'utente senza risposta una
   dietro l'altra. Il ragionamento di A lo dice esplicitamente: "In the previous turn, the user was asked…",
   "So now, I need to do everything that was accumulated: 1. … 2. …" (passo 5). Il modello prova a
   pianificare tutto l'arretrato in un unico turno, supera i 4096 token e si tronca di nuovo. Più l'arretrato
   cresce, più è facile troncarsi.
   Nel ragionamento di A compaiono 67 riferimenti ad "archiv" e 40 a "recall", contro 0 in B: il modello
   ragiona anche sulle parti archiviate. Il primo troncamento (passo 2, 07:40) però viene **prima** del
   primo mascheramento (07:53), e allo stesso passo B non si è troncata. In M (stessa config di B) il passo 2
   è finito in length come in A.
4. **Conclusione onesta.**
   - Il primo troncamento è un comportamento del modello con max_tokens 4096, ed è successo anche in M e in B.
   - Il proxy non introduce messaggi vuoti né cancella tool call.
   - La differenza sta in quello che segue. In B la compattazione di pi riassume e azzera la storia. Ha un
     costo (40% del tempo), ma rompe il ciclo. In A il proxy conserva fedelmente la storia, compresa la catena
     di richieste senza risposta, e il ciclo si autoalimenta per 24 passi.
   - Con n=1 non si può separare "proxy" da "percorso casuale del modello". Il meccanismo dell'arretrato
     però è visibile nei log e si può riprodurre.
   - **Proposta di fix (nel proxy, opzionale):** quando l'ultimo turno assistant è finito in `length` senza
     tool call, inserire o lasciare nella richiesta una breve nota di sistema del tipo "la risposta precedente
     è stata troncata: esegui un'azione per volta". In alternativa, contare i messaggi user consecutivi senza
     risposta e segnalarli. Lato configurazione: alzare `maxTokens` (8192) per i modelli con ragionamento
     lungo. Va provato con una corsa A' prima di dire che risolve.

## Altri fatti da sapere

- Al passo 1 di A l'agente ha lanciato `find / -name __init__.py` su un disco da 1,9 TB. Il comando è rimasto
  bloccato 25 min e l'ho chiuso a mano alle 07:37:46 (`run-A/interventi.log`). A ha quindi avuto ~25 min in
  meno, e ha finito comunque prima del timebox.
- A ha usato meno token (−29%), meno prefill (−30%) e ha fatto 1 sola rilettura da zero contro 38. Ma il 67%
  del suo tempo di richiesta è andato in turni troncati, senza produrre niente.
- B ha speso il 40% del tempo nei riassunti della compattazione: 24 richieste da 2–7K token lette da zero.

## Cosa è provato e cosa no

Provato (n=1 per lato, stesso compito, stessa build, stessi parametri):
- in 4 h, A completa tutti i 29 passi; B ne completa 10;
- A risponde a memoria bene alle sonde 8, 14 e 20 (17/18 domande), compresi i dati di file cancellati e le
  regole aggiornate. B alla sonda 8 non ricorda il lotto;
- il codice finale di A passa 87/87 test nascosti, compresi i 3 requisiti modificati. Quello di B passa 59/87;
- a parità di passo B produce codice e A no, fino al passo 25.

Non provato:
- che il vantaggio finale di A si ripeta: il codice è stato scritto in un solo passo (26), dopo 24 passi
  bloccati, e un percorso così non è affidabile;
- quanto avrebbe fatto B senza timebox;
- che la causa dei troncamenti a catena sia il proxy e non il caso: il primo troncamento avviene prima di
  qualsiasi intervento del proxy;
- DECISIONI.md e README: nessuna delle due corse li ha prodotti (A: passi vuoti; B: passi non raggiunti).

## File

`<ds4>/long-run2/`:
- prompts.txt, gen_data.py, run.sh, srv.sh, guard.sh, grade.py, steptext.py, table.py, hidsnap.py, diag*.py
- run-A/, run-B/: sessioni, trace, journal, analysis.json, grade.json, diag.txt, step-snaps/

`<cache>/salepren-hidden/`: test, risposte (pre e post correzione), riferimento, mutanti.

Copia su MVLINNA: `<promo>/ds4-long/RESULT2.md` e `ds4-long/salepren-task/`.
