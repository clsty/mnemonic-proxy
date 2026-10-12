# mnemonic-proxy 0.3.2 × ds4 (ultimo) × Qwen3.8 Flash Next Q2 su AI395: sessione lunga A/B/C

Card t_cc27eaa0, 11/10/2026. Host AI395 (Strix Halo, Radeon 8060S, ROCm). Tutti i numeri vengono dai log.
Niente stime.

## In breve

- **A (con proxy)**: 16 passi su 16 in 85 min. Tutte le trappole giuste (passo 10 e passo 16, 5 su 5).
  Nessuna rilettura da zero dopo la prima richiesta.
- **B (senza proxy, compattazione di pi)**: fermata dal timebox di 2 h al passo 14. 23 riletture da zero.
  Trappole: build_id giusto, terzo errore "non lo so" (onesto, non inventato).
  Passo 16 posto a parte, fuori timebox: 4 su 5, (c) "non lo so".
- **C (proxy + checkpoint_align_tokens=10240)**: 16 passi su 16 in 100 min. Passo 10 giusto.
  Passo 16: 4 su 5. La (a) è sbagliata: dice "mai discussi". Nel README ha scritto un build_id e un conteggio
  ERROR inventati.
- Il proxy toglie le riletture da zero: 0 contro 23. Token letti dal motore: 167 K (A) contro 267 K (B), con
  B che ha fatto meno passi.
- `checkpoint_align_tokens` **non ha avuto effetto misurabile**. Il proxy non ha mai spostato un pacchetto
  (`align_skipped=0` in 9 pacchetti su 9). I checkpoint usati restano gli stessi di A.

## Motore

- Clone nuovo `<ds4>/ds4-latest` da github.com/antirez/ds4 `main`, commit
  **`fc80bd695da76ee14bcb86820bf900a5cdfda806`** (7/10/2026, "Avoid full context rebuilds at DSpark response
  boundaries").
- **Upstream main non avvia Qwen3.8 su ROCm.** Errore all'avvio:
  `ds4: Qwen3.8 requires Metal or single-GPU CUDA (or --cpu --first-token-test)`.
  Prova conservata in `<ds4>/long-run/smoke-fail-upstream-main/`.
- Quindi, nel clone nuovo e su un ramo locale `main-plus-qwen-rocm`, ho applicato con cherry-pick i 2 commit
  ROCm locali già usati per la build `f7445c6` (`74f435c`, `f7445c6`, 6/10). Il cherry-pick è
  andato pulito. Commit risultanti: `e5ae3a2`, `6bcd400`. Il motore misurato quindi è
  **main fc80bd6 + 2 commit ROCm Qwen locali**. Non è la build `f7445c6` vecchia, che non è stata toccata.
- PR della issue #1201 (#1175, #1169, #1206, #1200): **tutte ancora aperte**, nessuna in `main`. I commit di
  main dopo la base `0aaea5a` riguardano DSpark, CUDA TP e Spark. Nessuno riguarda la cache Qwen.
  Le correzioni del riuso checkpoint/storia per Qwen **non sono in questa build**.
- Build: `LD_LIBRARY_PATH=<ds4>/compat-lib nice -n 19 ionice -c3 make -j12 strix-halo`, rc=0.

## Fumo (ctx 32768, `ds4bench.py`, 128 token generati, prompt freddo)

| modo | prompt | TTFT s | prefill tok/s | decode tok/s |
|---|---|---|---|---|
| senza MTP | 1571 | 19,01 | 82,6 | 12,6 |
| senza MTP | 7849 | 97,79 | 80,3 | 18,07 |
| `--mtp` | 1571 | 18,29 | 85,9 | 14,1 |
| `--mtp` | 7849 | 94,25 | 83,3 | 20,64 |

- Uguale alle misure del 6/10 (81–83 prefill, 15,7–19,3 decode, 20,8 con MTP).
- Memoria pianificata da ds4: 50,50 GiB. GTT misurata: 51,3–51,6 GiB.
- `--mtp` parte su ROCm, ma nel log non ci sono contatori di accettazione.
- Le corse A/B/C sono **senza MTP**, come le misure di riferimento.

## Compito lungo

- Script: `<ds4>/long-run/run.sh A|B|C`, prompt fissi in `prompts.txt` (16 passi), dati deterministici da
  `gen_data.py` (seed 20261011). md5: prompts `f4a99662…`, gen_data `4bc4e22f…`, run.sh `849ef3a3…`.
- Compito: pacchetto Python `farmastock` (inventario, report, movimenti, validazione, export JSON, refactoring,
  lowstock, README) con test unittest. Uscite voluminose: `cat` di deploy.log (12,2 K token), movements.log
  (10,7 K), stock.csv (8,0 K) e stock_feb.csv (6,7 K), più `cat farmastock/*.py` e le suite di test.
- Trappole (risposte in `traps.json`):
  - passo 1: `cat deploy.log`. Poi il file viene **tolto dalla cartella**.
  - passo 2: nota solo in chat: «Orsa Minore», consegna 24 novembre.
  - passo 3: decisione: prezzi in centesimi interi.
  - passo 10: build_id `BX-7Q4K-2291`; terzo errore `rq-73190`, shard 4.
  - passo 16: (a) Orsa Minore / 24 novembre; (b) build_id; (c) rq-73190 shard 4; (d) 4 righe ERROR;
    (e) centesimi.
- Timebox: 7200 s per corsa. KV su disco svuotato prima di ogni corsa.

Comandi esatti, tutti in `<ds4>/long-run/`:

```
srv.sh:   nice -n 19 ionice -c3 ./ds4-server --rocm -m <ds4>/ds4-qwen-rocm/gguf/Qwen3.8-Flash-Next-Q2.gguf \
            --ctx 32768 --port 8130 -t 12 --kv-disk-dir <ds4>/long-kv --kv-disk-space-mb 12288 --trace <run>/trace.json
proxy:    nice -n 19 ionice -c3 venv-proxy/bin/mnemonic-proxy --upstream http://127.0.0.1:8130 --port 8131 \
            --data <run>/proxy-data --config config-<A|C>.json --tokenizer tokenizer-qwen38.json
pi:       nice -n 19 pi --provider ds4proxy|ds4direct --model qwen3.8-flash-next-q2 --session-dir <run>/sessions --continue -p "<passo>"
```

- Proxy: `pip install mnemonic-proxy==0.3.2` in `venv-proxy`. Config: `examples/config.ds4.json` del tag
  v0.3.2. Per C ho cambiato solo `checkpoint_align_tokens: 10240`.
- Per C il valore viene da ds4: `--kv-cache-continued-interval-tokens` vale 10000 di serie, arrotondato a
  `--kv-cache-boundary-align-tokens` 2048, quindi 10240 (`ds4_kvstore.c`, `kv_cache_continued_step`).
- Tokenizer: `tokenizer.json` di Qwen/Qwen3.8-Flash-Next (12 MB, non è un modello). Serve perché l'allineamento
  abbia senso. È usato in A e in C, così l'unica variabile tra A e C è l'allineamento.
- Il proxy ha letto la finestra 32768 da ds4 e ha scalato le soglie ×0,25: mask_trigger 20000, mask_target
  10000, keep_recent 4000, min_batch 4000.
- pi A/C (`pi-agent-proxy`): compattazione di pi spenta. La finestra la gestisce il proxy: pi vede 131072.
- pi B (`pi-agent-direct`): contextWindow 32768, compattazione nativa accesa con `reserveTokens 8192`,
  `keepRecentTokens 8000`. I valori di serie (16384/20000) non stanno in 32K: scatterebbe a 16K e terrebbe
  20K. È una scelta mia, dichiarata qui.
- maxTokens 4096 per risposta in tutte e tre le corse. pi 1.0.3.

## Tabella A/B/C

| misura | A proxy | B diretto | C proxy+align |
|---|---|---|---|
| passi completati | 16/16 | 14/16 (timebox al 14) | 16/16 |
| durata | 5109 s | 7200 s (timebox) | 6007 s |
| richieste a ds4 | 106 | 95 | 120 |
| token letti dal motore, totale | 167 253 | 267 195 | 208 951 |
| token letti per richiesta: media / p50 / p90 / max | 1578 / 60 / 6455 / 20978 | 2813 / 80 / 10683 / 18405 | 1741 / 108 / 8133 / 18896 |
| richieste con ≥4000 token letti | 13 | 25 | 14 |
| riletture da zero (`ctx=0..`) dopo la prima | 0 | 23 | 0 |
| live kv cache miss (tutti `token-mismatch`) | 11 | 25 | 12 |
| miss con common=0 | 0 | 0 | 0 |
| miss con common<4096 | 5 | 24 (common=3 o 65) | 6 |
| ripresa da checkpoint su disco (hit) | 11 (47 104 tok) | 2 (28 672 tok) | 12 (32 768 tok) |
| TTFT server (prefill): media / p50 / p95 / max s | 20,0 / 1,8 / 140,9 / 252,2 | 34,9 / 2,0 / 155,7 / 225,9 | 22,2 / 2,5 / 150,8 / 230,3 |
| prefill tok/s (richieste ≥1000 token) | 81,9 | 81,8 | 81,2 |
| decode tok/s (richieste ≥32 token generati) | 18,83 | 19,21 | 18,94 |
| token generati | 55 933 | 73 769 | 63 055 |
| pacchetti di masking / cambi di segmento | 8 / 3 | – | 9 / 3 |
| compattazioni di pi | 0 | 7 | 0 |
| recall (chiamate, usate) | 1, 1 usata | – | 7, 7 usate (2 tagliate per spazio) |
| trappole passo 10 (build_id, 3° errore) | 2/2 esatte | 1/2, l'altra "non lo so" | 2/2 esatte |
| trappole passo 16 (a–e) | 5/5 esatte | 4/5, (c) "non lo so" (*) | 4/5, (a) sbagliata |
| fatti inventati | 0 | 0 | 1: README con build_id `7f3a9c2...45ce` e "5 ERROR" |
| test finali (`unittest discover`) | 57 OK | 40 OK | 42 OK |
| errori ds4 / proxy | 0 / 0 | 0 / – | 0 / 0 |
| exit di pi ≠0 | 0 | 1 (rc=124, timebox) | 0 |
| MemAvailable minima | 50,6 GiB | 50,7 GiB | 47,9 GiB |
| GTT massima | 51,5 GiB | 51,6 GiB | 51,7 GiB |
| long-kv massimo | 11,8 GiB | 12,0 GiB | 12,0 GiB |

(*) B non è arrivata al passo 16 entro il timebox. Ho posto **solo la domanda 16** alla stessa sessione pi,
dopo la corsa e fuori timebox (`extraB16.sh`, `run-B/extra16.log`). Non conta nella durata. Il primo
tentativo è fallito: il server non partiva per una cartella della trace mancante. Il secondo è andato.

"TTFT server" è il tempo di prefill registrato da ds4 (`prompt done`): non ho misurato il TTFT lato client.
Il miglior TTFT è il p50 basso: la maggior parte delle richieste riusa la cache viva e legge da 20 a 150 token.

## Cosa si vede

- **B (senza proxy)**: a ogni compattazione pi manda due richieste nuove. Prima il riassunto (prompt diverso,
  `common=3`), poi il contesto compattato, che ds4 rilegge da zero. In tutto 23 riletture da 1–18 K token.
- **B, passo 12**: è entrato in un giro. Il riassunto di pi su 5193 token è arrivato al tetto di 4096 token
  (`finish=length`) per 4 volte di seguito, con circa 270 s ogni volta. Il passo 12 è durato 21,5 min.
  Per questo B ha superato le 2 h.
- **A e C (con proxy)**: i cambi di prompt (masking e cambio di segmento) ripartono quasi sempre da un
  checkpoint su disco (2048 o 10240 token) o dal prefisso comune vivo. Mai da zero. Le note di segmento sono
  generate sulla cache viva (`cached` 23 944–27 536 su 27–28 K).
- **C, `checkpoint_align_tokens`**: in tutti i 9 pacchetti `align_skipped=0`. Il primo messaggio cambiato
  stava già vicino a un multiplo di 10240, oppure i candidati non bastavano per saltarne.
  - Offset stimati dei primi cambi: 2276, 2811, 2482, 8039, 8177, 4604, 10006, 16379, 4456.
  - ds4 ha ripreso 11 volte su 12 dal checkpoint da 2048 e una volta da quello da 10240. È lo stesso schema di A.
  - La differenza di token letti tra A e C (167 K contro 209 K) dipende dal percorso diverso del modello
    (120 richieste contro 106, più recall). Non dipende dall'allineamento.
- **C, trappola (a)**: la nota del passo 2 era in archivio (pezzo `rc52cbcf4dea0`, ruolo user).
  - Al passo 16 il modello ha cercato con `queries` giuste e il recall l'ha trovata (rank 0).
  - Ma il risultato è stato **tagliato per spazio** (`recall_trimmed room=-447`). Il modello ha visto solo
    l'avviso di taglio e ha concluso "mai discussi".
  - In A la stessa nota era passata nelle note di segmento: le note scritte dal modello la riportavano.
    In C le note del primo cambio di segmento sono uscite vuote (`notes tokens=0`, 1121 token generati
    tutti di ragionamento) e la nota si è persa da lì.
- **C, invenzione nel README (passo 14)**: "5 righe ERROR, build_id 7f3a9c2...45ce". Al passo 16 il modello
  stesso l'ha segnalata come errore, dopo il recall del log originale.
- **Velocità**: prefill 81–82 tok/s e decode 18,8–19,2 tok/s, uguali in tutte e tre le corse e al fumo.
  Il proxy non rallenta il motore.

## Cosa è provato

- ds4 main fc80bd6 da solo non gira con Qwen3.8 su ROCm. Con i 2 commit ROCm locali gira, alla stessa
  velocità della build del 6/10.
- In questa sessione lunga a 32K, con un solo campione per corsa:
  - il proxy evita tutte le riletture da zero (0 contro 23);
  - legge il 37% di token in meno (A contro B);
  - finisce il compito entro il timebox, mentre B no;
  - conserva i fatti iniziali meglio della compattazione di pi (A 7/7, C 6/7, B 5/7 contando anche il passo 16
    fuori timebox).
- `checkpoint_align_tokens=10240` con ds4 a 32K non ha cambiato nessuna decisione di masking in questa corsa.
- Memoria: GTT ferma a ~51,6 GiB. MemAvailable mai sotto 47,9 GiB. La guardia non è mai scattata.

## Cosa non è provato

- Un solo campione per corsa. Il modello prende strade diverse a ogni corsa (richieste: 106, 95, 120), quindi
  le differenze piccole (A contro C) non sono significative.
- Le PR #1169, #1175, #1206 e #1200 di ds4 non sono in main: il loro effetto non è misurato.
- Il TTFT lato client e le corse con `--mtp` sulla sessione lunga non sono misurati.
- B usa soglie di compattazione scelte da me per 32K. Con altre soglie il numero di compattazioni cambierebbe.
- L'allineamento potrebbe servire con finestre più grandi (più pacchetti candidati) o con un intervallo di
  checkpoint più piccolo. Qui non è provato.
- Il taglio del recall quando il contesto è pieno (C, passo 16) è un punto debole del proxy visto una volta.
  Va riprodotto prima di trarne conclusioni.

## Pulizia e stato finale

- Nessun mio processo attivo: ds4-server, proxy, pi e guardia sono fermi. Porte 8130 e 8131 libere.
- `<ds4>/long-kv` cancellata (alla fine conteneva 12 GiB).
- Disco `/`: 59 GiB liberi (97% usato), come all'inizio. RAM: 101 GiB disponibili su 122.
- Restano su disco:
  - `<ds4>/ds4-latest`: 471 MB, ramo `main-plus-qwen-rocm`;
  - `<ds4>/long-run`: 119 MB, con log, trace, sessioni, giornali del proxy e `analysis.json` per corsa.
- Non ho toccato llama-swap, il container sqlserver (fermo), i browser e le build `<ds4>/ds4` e `<ds4>/ds4-qwen-rocm`.
- Nessun push e nessun commento su ds4.

## File

- `run-{A,B,C}/`: `server.log` di ds4, `trace.json`, `session.log` di pi, `sessions/`, `proxy-data/journal.jsonl`
  e `archive.sqlite`, `analysis.json`, `task/` (il codice prodotto).
- `analyze.py`: le misure della tabella. `events.py`: gli eventi del proxy. `pisess.py`: compattazioni e
  strumenti della sessione pi.
- `guard.sh` e `guard-all.log`: campioni ogni 10 s (MemAvailable, GTT, dimensione di long-kv).
