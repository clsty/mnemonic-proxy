# mnemonic-proxy 0.3.2 × ds4 × DeepSeek V4 Flash Q2 su AI395 (ROCm ufficiale): corsa breve di riferimento
Card t_a9c962c4, 12/10/2026 notte. Host AI395 (Strix Halo, Radeon 8060S gfx1151, GTT 124 GiB).
Tutti i numeri vengono dai log (`<ds4>/long-run/flash/`). Confronto con la corsa A Qwen3.8 della card t_cc27eaa0.

## In breve
- **Flash pre-0731 si carica e gira sulla ds4 ufficiale** (`origin/main`, build `make strix-halo`, nessuna patch).
- **Corsa con proxy: 16 passi su 16 in 61 min** (Qwen A: 85 min). 0 riletture da zero dopo la prima richiesta.
  Test propri dell'agente: 29, tutti OK.
- **Trappole: 7 su 8 risposte giuste, 1 "non lo so".** Passo 10: build_id giusto, terzo errore
  "non l'ho memorizzato" (onesto, non inventato). Passo 16: 5 su 5, il terzo errore recuperato con `recall`
  dall'archivio del proxy. Qwen A: tutto giusto anche al passo 10.
- **Problema di memoria trovato**: con le impostazioni di default ds4 riempie la GTT con una cache q8→fp16
  finché restano 8 GiB liberi di GTT; su AI395 la GTT è quasi tutta la RAM, quindi MemAvailable scende a
  ~9 GB (fumo 1, guardia scattata, nessun OOM). Spenta con `DS4_CUDA_NO_Q8_F16_CACHE=1` (variabile già
  letta dal runtime ROCm di ds4): MemAvailable minima 13,2 GiB nella corsa. Margine reale piccolo.

## Motore e modello
- ds4 `origin/main` **`fc80bd695da76ee14bcb86820bf900a5cdfda806`** (7/10/2026), worktree pulito
  `<ds4>/ds4-flash-main` (detached), nessun commit locale.
  Build: `LD_LIBRARY_PATH=<ds4>/compat-lib nice -n 19 ionice -c3 make -j12 strix-halo`, rc=0
  (compat-lib serve solo perché l'lld di ROCm 7.2.1 cerca libxml2.so.2; è la stessa build della card padre).
- Modello: `<models>/DeepSeek-V4-Flash-IQ2XXS-w2Q2K-AProjQ8-SExpQ8-OutQ8-chat-v2-imatrix.gguf`,
  86.720.111.488 byte, sha256 `efc7ed607ff27076e3e501fc3fefefa33c0ed8cf1eff483a2b7fdc0c2e616668`
  (verificato il 21/09/2026). È **pre-0731**: non è il `ds4f-q2` attuale (Flash 0731) che docs/MODELS.md
  consiglia. Il caricamento è andato a buon fine, nessun errore nel log.
- Memoria pianificata (log di avvio):
  `KV 0.78 GiB (raw 0.36 + compressed 0.42) + buffers 0.25 GiB + resident model 80.76 GiB = 81.79 GiB planned`
  (ctx=32768, prefill_chunk=4096). Preparazione del modello 57 s, server pronto in ~70 s.
- Proxy: mnemonic-proxy 0.3.2 (`<ds4>/long-run/venv-proxy`), `config.ds4.json` identica alla corsa A,
  tokenizer `tokenizer.json` di `deepseek-ai/DeepSeek-V4-Flash` (HF) per i conteggi esatti.
- pi: stessi parametri della corsa A (`compaction.enabled=false`, contextWindow dichiarata 131072,
  maxTokens 4096), cartella `pi-agent-flash`.

## Comandi
```
# server (flash/srv.sh)
DS4_CUDA_NO_Q8_F16_CACHE=1 nice -n 19 ionice -c3 ./ds4-server --rocm -m <gguf sopra> \
  --ctx 32768 --port 8140 -t 12 --kv-disk-dir <ds4>/flash-kv --kv-disk-space-mb 10240 --trace <dir>/trace.json
# proxy
nice -n 19 ionice -c3 venv-proxy/bin/mnemonic-proxy --upstream http://127.0.0.1:8140 --port 8141 \
  --data run-F/proxy-data --config config-F.json --tokenizer tokenizer-dsv4.json
# corsa: flash/run.sh (TIMEBOX=4800 s), stessi prompts.txt / gen_data.py / traps.json della card padre
# guardia: flash/guard.sh, ogni 5 s; MemAvailable < 12 GB -> stop di ds4/proxy/pi
```

## Fumo (ds4bench, 128 token generati, ctx 32768)
Il prompt è lo stesso testo della card padre; con il tokenizer DeepSeek viene più corto (1221 / 6021 token
invece di 1571 / 7849 di Qwen).

| config | token prompt | TTFT s | prefill tok/s | decode tok/s |
|---|---:|---:|---:|---:|
| Flash, default (cache q8→fp16 attiva) | 1221 | 12,02 | 101,6 | 14,54 |
| Flash, default (cache q8→fp16 attiva) | 6021 | 29,70 | 202,7 | 13,70 |
| Flash, `DS4_CUDA_NO_Q8_F16_CACHE=1` (usata nella corsa) | 1221 | 10,90 | 112,0 | 14,87 |
| Flash, `DS4_CUDA_NO_Q8_F16_CACHE=1` (usata nella corsa) | 6021 | 49,88 | 120,7 | 13,75 |
| Qwen3.8 Q2 (card padre, senza MTP) | 1571 | 19,01 | 82,6 | 12,6 |
| Qwen3.8 Q2 (card padre, senza MTP) | 7849 | 97,79 | 80,3 | 18,07 |

- La cache q8→fp16 vale circa ×1,7 sul prefill lungo (202 contro 121 tok/s), ma costa la RAM:
  fumo 1 MemAvailable min **8,6 GiB**, GTT max 94,8 GiB, guardia scattata 7 volte (dopo il bench, server
  spento normalmente, llama-swap rimasto attivo, nessun OOM nel kernel log).
  Fumo 2 (cache spenta): MemAvailable min 14,8 GiB, GTT max 88,6 GiB.
- Riferimento giugno (`bench-baseline.txt`, build più vecchia): 150–178 tok/s prefill, 13,3–15,3 decode.

## Corsa con proxy (come corsa A)
| misura | Flash (questa card) | Qwen3.8 A (t_cc27eaa0) |
|---|---:|---:|
| passi completati | **16/16** | 16/16 |
| durata | **3661 s (61 min)** | 5109 s (85 min) |
| richieste a ds4 | 68 | 106 |
| token letti dal motore, totale | 180.451 | 167.253 |
| token letti per richiesta: media / p50 / p90 / max | 2654 / 112 / 10.257 / 22.367 | 1578 / 61 / 6455 / 20.978 |
| richieste con ≥ 4000 token letti | 12 | 13 |
| riletture da zero dopo la prima | **0** | 0 |
| live kv cache miss (tutti token-mismatch) | 9 (common < 4096: 3) | 11 (5) |
| hit KV su disco / token recuperati | 9 / 20.259 | 11 / 47.104 |
| TTFT server: media / p50 / p95 / max (s) | 23,7 / 2,34 / 130,4 / 190,3 | 20,0 / 1,81 / 140,9 / 252,2 |
| prefill tok/s (richieste ≥ 1000 token) | **115,2** | 81,9 |
| decode tok/s (gen ≥ 32) | 12,99 | 18,83 |
| token generati | 26.422 | 55.933 |
| contesto massimo raggiunto | 28.337 | 28.342 |
| mascheramenti del proxy | 8 | 8 |
| cambi di segmento | 1 (passo 13, note 2198 token) | 3 |
| chiamate recall | 2 (passo 16) | 1 |
| trappole | **7 giuste + 1 "non lo so"** | 7/7 |
| MemAvailable min / GTT max | **13,2 GiB** / 88,7 GiB | 50,6 GiB / 51,5 GiB |
| KV su disco max | 4,6 GiB | 11,8 GiB |
| guardia / timebox | mai scattata / no | mai / no |
| test propri dell'agente alla fine | 29 OK | — |

Trappole (risposte attese in `traps.json`):
- Passo 10 (senza recall): build_id `BX-7Q4K-2291` giusto; terzo errore: "non ho memorizzato né il request
  id né lo shard. Per rispondere dovrei rileggere l'output, ma hai…" → non risposto, non inventato.
- Passo 16: (a) «Orsa Minore», 24 novembre ✓; (b) `BX-7Q4K-2291` ✓; (c) `rq-73190`, shard 4 ✓ (dalla riga
  originale recuperata con `recall` id + query "ERROR" nell'archivio); (d) 4 ✓; (e) centesimi interi ✓.

## Cosa è provato
- La configurazione documentata da ds4 per Strix Halo (main ufficiale, `make strix-halo`, `--rocm`, Flash
  Q2 residente) regge una sessione agentica di 16 passi con pi + mnemonic-proxy 0.3.2 a contesto 32K:
  nessuna rilettura da zero, nessun errore del server o del proxy.
- Rispetto a Qwen3.8 (ROCm non ufficiale): prefill più rapido (115 contro 82 tok/s), decode più lento
  (13,0 contro 18,8), sessione più corta perché Flash genera la metà dei token (26K contro 56K).
- Il proxy funziona allo stesso modo con un tokenizer diverso: stessi 8 mascheramenti, 1 cambio di segmento,
  recall usata per recuperare un dato esatto ormai uscito dalla finestra.

## Cosa non è provato
- n=1, nessuna corsa senza proxy con Flash: non dice nulla sul guadagno del proxy con questo modello.
- Modello **pre-0731**: il modello di riferimento attuale di ds4 è Flash 0731 (non scaricato: su `/`
  54 GB liberi, servono ~81 GiB).
- La corsa è stata fatta con la cache q8→fp16 **spenta**: la configurazione di default è più veloce nel
  prefill ma lascia ~9 GB di RAM disponibile su AI395 con le altre app aperte; non è stata provata in
  una corsa lunga.
- Il passo 10 sbagliato a metà non è confrontabile con certezza con Qwen: Qwen ha usato recall anche lì,
  Flash no (dipende dal modello, non dal proxy: il proxy dava lo stesso suggerimento).

## File
- `<ds4>/long-run/flash/`: srv.sh, smoke.sh, run.sh, guard.sh, config-F.json, tokenizer-dsv4.json,
  pi-agent-flash/, smoke1-q8f16/ (fumo default), smoke/ (fumo cache spenta), run-F/ (server.log, trace.json,
  proxy-data/journal.jsonl, session.log, sessions/, task/, analysis.json), guard-smoke1.log, guard.log,
  STOP-smoke1 (scatti della guardia nel fumo 1).
- Build riusabile: `<ds4>/ds4-flash-main` (worktree di `<ds4>/ds4-latest` su origin/main fc80bd6).
- `<ds4>/flash-kv` cancellata; nessun processo della card attivo.
