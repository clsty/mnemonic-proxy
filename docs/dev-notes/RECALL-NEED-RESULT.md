# RECALL-NEED — il modello usa recall senza che glielo si chieda?

Qwen3.8 Flash Next IQ3_XXS su Strata 0.1.40, RTX 4070 Ti 12 GB, mnemonic-proxy 0.3.1. Ottobre 2026.


In breve: il problema non si è presentato. Con il proxy di produzione (config 1, nessun aiuto) Flash Next ha
fatto recall di sua iniziativa e ha scritto i valori giusti in tutte e 3 le varianti valide (A, B, D). La
variante C non vale: l'agente si era fatto una copia di sicurezza del file. Per la regola del brief (config 1
riuscita su almeno 3 varianti su 4) mi sono fermato dopo 4 episodi invece di 16. Raccomandazione: non procedere
per ora con ricevute parlanti né con il grilletto. La patch resta su un branch locale.

## 1. Audit offline delle sessioni (CPU)

Script: `scripts/audit_need.py`, che estende `audit3h*.py`/`audit_all.py` (copia in
`audit/`). Ho analizzato 18 sessioni con almeno 50 righe di
`dati delle sessioni `: 8 originali e 10 rigiochi (deduplicati con `lib.sessions()`). Ho escluso i
journal identici byte per byte. Dati per sessione: `audit/audit_sessioni.csv`. Elenco delle recall con il
messaggio utente: `audit/recall.csv`. Dettagli ed esempi: `audit/audit.json`.

| (8 sessioni originali: 4 pi, 3 Claude Code, 1 Codex) | valore |
|---|---|
| recall dopo una domanda esplicita sul passato (tutti i journal, dedup) | 108 (171,9K token restituiti) |
| recall spontanee (nessuna domanda sul passato) | **5**, tutte nella sessione Claude Code `c5c7ee0681130`, durante una revisione ("rileggi tutti i file…") |
| recall su istruzione del proxy / non determinabili | 1 / 1 |
| riletture dello stesso file | 209: 136 con lettura precedente visibile, 65 mascherata, 8 tagliata dal segmento |
| riletture **evitabili** (lettura precedente mascherata, file non modificato nel frattempo) | **30, 36,9K token** (46,2K contando anche i rigiochi) |
| edit falliti (31 su 505) per causa | file cambiato dopo la lettura 10, mai letto 8, ambiguo ("appears N times") 3, validazione 3, copia sbagliata da lettura visibile 3, **memoria da lettura nascosta 4** |
| auto_recall su messaggi utente veri / su notifiche o messaggi sintetici | 112 / 12; token iniettati 49,8K / 9,7K (le 12 sintetiche stanno tutte nella sessione 3h15 `caeaa81de2522`) |
| "gemelli" (valore chiave=numero citato dall'assistente confrontato con l'ultimo valore visto in un output) | 63 coerenti, 26 valore vecchio ma l'ultimo era **visibile**, 2 valore vecchio con l'ultimo nascosto, 17 mai osservati |

Lettura: nelle sessioni vere le recall spontanee sono rare (5 su 113). Le riletture evitabili costano poco
(circa 37K token su 7.000 righe di sessione). Gli edit falliti per memoria sono 4 su 505. La confusione con un
valore vecchio avviene quasi sempre con l'ultimo valore ancora visibile, quindi senza colpa del mascheramento.

## 2. Scenario sulla GPU (Flash Next IQ3_XXS, Strata 0.1.40, pi 0.87.1)

Configurazione:
- Copia del proxy 0.3.1 in `proxy-src`, branch locale `recall-need`, commit
  `bb0184d`. Ho rimosso il remote, quindi niente push possibili.
- Motore di prova su :8195 con la configurazione di produzione. Catena: relay che registra i prompt fisici →
  proxy copia su :8296 → pi in `-p --mode json` con una sessione persistente, un comando per turno, solo
  strumenti di base e niente estensioni.
- Soglie di mascheramento basse (trigger 9K, target 5K, coda protetta 2,5K) perché gli episodi sono piccoli
  (12-19K token).
- Progetto finto `ledger` con un bug vero nei test. Turni: preparazione con il dato, poi correzione del bug,
  `--format json` con test, README, e infine la richiesta finale senza "ricordi/prima".

Prova a secco su CPU (`scenario/dryrun_proxy.py`, esito OK su 16 combinazioni su 16):
- c1-c3: uscita critica mascherata alla richiesta finale, nessun valore vero nel prompt.
- c4: tutti i valori visibili.
- c2: la ricevuta contiene nomi e nessun valore.
- c3: il 📎 compare sulla richiesta finale e non sulle notifiche.

La prima versione falliva su B e C: i numeri a 2 cifre (es. "25") comparivano per caso altrove nel prompt. Ho
corretto i generatori (valori a 3 cifre, testi più lunghi così che vengano mascherati) prima di usare la GPU.

| variante (config 1, proxy attuale) | esito | valido (dato assente dal prompt) | recall nel turno finale | tempo |
|---|---|---|---|---|
| A output casuale di `prepare.sh` (BUILD_ID, p95, 3 migrazioni) | **giusto via recall**, 5/5 valori | sì | 2 (`recall id=…`) | 300 s |
| B file letto e poi cancellato (porta, retention, regione) | **giusto via recall**, 3/3 | sì | 1 | 205 s |
| C file sovrascritto, senza git | giusto, 3/3 ma **non valido** | no: al turno 2 l'agente aveva creato `config.yaml.v1.bak` prima di lanciare `gen_config.sh` | 0 | 353 s |
| D errore di un servizio poi spento (codice, host, pin) | **giusto via recall**, 3/3 | sì | 1 (più 2 nei turni prima) | 293 s |

Esempi:
- A: la ricevuta nel prompt diceva solo "command succeeded … Exact text: recall id=…". Il modello ha chiamato
  `recall id=rd23105a1e206`, ha scritto `bld-b75f39ed`, p95 870.6 e le 3 migrazioni giuste, e ha aggiunto
  nel file che rilanciare lo script darebbe valori diversi.
- B: "now archived to the portal, so I used the exact text I recorded", dopo `recall id=r75482e824a5d`.
- D: ha rilanciato `smoke.sh`, ma nel ticket ha messo i valori della prima esecuzione presi con la recall
  (PGW-4088). Nessun gemello.

Costi:
- Servizio :8096 fermo 23 minuti (dalle 23:42:20 alle 00:05:24). Produzione riaccesa dal trap e verificata
  (:8095 e :8096 ok).
- Episodi da 35-50 richieste. Il turno con più lavoro (correzione del bug) dura 2-4 minuti.
- Recall: 0,8-1,3K token per episodio.
- Il TTFT della richiesta finale non è misurato bene: il relay registra il primo byte dello stream (0,03-0,05 s),
  non il primo token.
- c2 e c3 non sono andati su GPU. Dalla prova a secco il costo stimato è circa +120-165 token di prompt per le
  ricevute parlanti e +90-120 per il 📎, cioè circa l'1-2% su questi episodi.

## Raccomandazione

- **Ricevute parlanti (c2) e grilletto 📎 (c3): fermare.** Con pi e Flash Next la ricevuta attuale
  (`recall id=…`) basta: il modello fa recall da solo quando il dato serve e non è su disco. L'osservazione di
  Cline (recall solo su domanda esplicita) dipende probabilmente dal client e dal modello, non dal proxy.
  L'audit va nella stessa direzione: le occasioni reali di "bisogno non richiesto" sono poche (4 edit per
  memoria, 30 riletture evitabili).
- Limiti di questa conclusione:
  - una sola ripetizione;
  - episodi corti (meno di 20K token, 4-10 pacchetti di mascheramento);
  - c4 non eseguito, quindi le varianti non sono validate dal tetto (inutile visto che c1 riesce);
  - un solo client (pi).
- Per riaprire la questione:
  - rifare la variante C impedendo copie su disco, ad esempio con `gen_config.sh` lanciato dall'utente fuori
    dall'agente;
  - provare sessioni lunghe (oltre 60K token, con cambio di segmento);
  - provare un client tipo Cline o Claude Code.
- Da sistemare a parte: l'auto_recall che scatta sulle notifiche. È già risolto nella versione attuale: le 12
  sintetiche sono tutte nella sessione del 5/10.


# Parte 2 — Claude Code, C senza copie, sessione lunga (12/10/2026)

## Esito in breve

- **Claude Code + proxy 0.3.1 (c1): 9 episodi su 9 giusti, sempre con recall spontanea.** Fra questi, 2 C' e la sessione lunga.
- **Sessione lunga (>60K token, cambi di segmento), c1: giusta via recall sia con Claude Code (127K virtuali, 3 cambi) che con pi (231K virtuali, 6 cambi).**
- c4 (tetto, niente mascheramento): sempre giusto (11/11), quindi le varianti sono valide. Un caso misto (cc-c4-L, sotto).
- **Cline: non provato.** Headless non praticabile in 30 min (dettagli sotto).
- c2/c3 non servono: c1 non ha mai fallito dove c4 riusciva.
- Servizio :8096 fermo 3 h 05 min (00:39–03:44), sotto il tetto di 4 h. Produzione riaccesa dal trap; :8095 e :8096 ok.

## Setup

- Claude Code 2.1.284 `-p --resume`, con `CLAUDE_CONFIG_DIR` separato per episodio. Memoria automatica e checkpoint dei file sono spenti, `DISABLE_AUTO_COMPACT=1`.
- Catena: copia proxy-src (0.3.1 + branch `recall-need`, c2/c3 spenti) → relay → Strata 0.1.40 di prova su :8195.
- pi 0.87.1 solo per la sessione lunga.
- Episodi corti: soglie della parte 1 (mask_trigger 9000, target 5000).
- Sessione lunga, c1: le soglie di produzione scalate ×0,25 a finestra 32K, come fa il proxy da solo con un motore a 32K: mask_trigger 20000, target 10000, keep_recent 4000, min_batch 4000, window 32768. Così il cambio di segmento arriva in tempi ragionevoli.
- Sessione lunga, c4: finestra 131072 senza mascheramento.
- **C' (C rifatta):** `gen_config.sh` sta fuori dal progetto e lo lancia il driver fra due turni. Il progetto non ha git. Dopo il lancio il driver cancella ogni file che contenga chiave+valore vecchi: 0 trovati nei 4 episodi. La richiesta finale non dice "ricordi/prima".
- **Sessione lunga (L):**
  - Al turno 0 si lancia `prepare.sh` casuale (come A). Poi seguono 12 turni pesanti: log da 16K, lint, benchmark, revisione file, INCIDENTS.md. Alla fine, RELEASE.md.
  - Il dato critico esiste solo nell'output del turno 0.
- Verità salvate fuori dalla cartella dell'episodio (`ep2-truth/`).
- `valido`: c1 non deve avere alcun valore vero nel prompt fisico del turno finale. In C' si conta chiave+valore, perché "200" compariva per caso nella versione del kernel.

## Tabella

vis = valori veri visibili nel prompt finale; rec = chiamate recall nel turno finale; tok = token da recall; virt = storia virtuale max; sw = cambi segmento

| client | var | cfg | rep | esito | valido | giusti | vis | rec | tok | s | virt | sw |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cc | A | c1 | 1 | giusto_recall | sì | 5/5 | 0 | 1 | 625 | 278 | 33442 | 0 |
| cc | A | c1 | 2 | giusto_recall | sì | 5/5 | 0 | 1 | 632 | 442 | 47256 | 0 |
| cc | B | c1 | 1 | giusto_recall | sì | 3/3 | 0 | 5 | 934 | 359 | 39003 | 0 |
| cc | B | c1 | 2 | giusto_recall | sì | 3/3 | 0 | 1 | 551 | 331 | 38997 | 0 |
| cc | C' | c1 | 1 | giusto_recall | sì | 3/3 | 0 | 1 | 441 | 318 | 39328 | 0 |
| cc | C' | c1 | 2 | giusto_recall | sì | 3/3 | 0 | 1 | 439 | 236 | 32440 | 0 |
| cc | D | c1 | 1 | giusto_recall | sì | 3/3 | 0 | 1 | 223 | 225 | 36389 | 0 |
| cc | D | c1 | 2 | giusto_recall | sì | 3/3 | 0 | 1 | 222 | 256 | 37698 | 0 |
| cc | L | c1 | 1 | giusto_recall | sì | 5/5 | 0 | 1 | 631 | 1181 | 126924 | 3 |
| pi | L | c1 | 1 | giusto_recall | sì | 5/5 | 0 | 5 | 1681 | 2844 | 231240 | 6 |
| cc | A | c4 | 1 | giusto_altro | sì | 5/5 | 5 | 0 | 0 | 273 | 36179 | 0 |
| cc | A | c4 | 2 | giusto_recall | sì | 5/5 | 5 | 1 | 2643 | 249 | 34661 | 0 |
| cc | B | c4 | 1 | giusto_altro | sì | 3/3 | 3 | 0 | 0 | 140 | 27159 | 0 |
| cc | B | c4 | 2 | giusto_altro | sì | 3/3 | 3 | 0 | 0 | 200 | 31494 | 0 |
| cc | C' | c4 | 1 | giusto_recall | sì | 3/3 | 3 | 2 | 730 | 245 | 33510 | 0 |
| cc | C' | c4 | 2 | giusto_altro | sì | 3/3 | 3 | 0 | 0 | 257 | 34582 | 0 |
| cc | D | c4 | 1 | giusto_altro | sì | 3/3 | 3 | 0 | 0 | 166 | 29418 | 0 |
| cc | D | c4 | 2 | giusto_altro | sì | 3/3 | 3 | 0 | 0 | 182 | 29436 | 0 |
| cc | L | c4 | 1 | misto_gemello | sì | 5/5 | 5 | 0 | 0 | 1698 | 191747 | 1 |
| pi | L | c4 | 1 | giusto_altro | sì | 5/5 | 5 | 0 | 0 | 1022 | 86248 | 0 |

In c4 la recall a volte compare anche se tutto è visibile: il modello usa lo strumento quando c'è.

## Sessione lunga

- **cc c1:**
  - Il dato è al turno 0. Nel turno finale la storia virtuale era di 127K token, il prompt fisico ≤26K.
  - Ci sono stati 3 cambi di segmento: 752 s e 238 s prima della richiesta finale, più un terzo durante la richiesta stessa.
  - Le note del segmento 1 citano l'id `r71f1b62335b0` ("prepare.sh output…") ma non i valori.
  - Il modello ha fatto `recall id=r71f1b62335b0` e ha scritto bld-734cd501 / 826.1 / 0031,0055,0067. Ha specificato "from the archived prepare.sh output rather than re-running".
  - Nel prompt finale non c'erano BUILD_ID né p95. C'erano invece i soli numeri delle migrazioni (senza nome), dentro un documento scritto dall'agente stesso (INCIDENTS.md).
- **pi c1:**
  - 6 cambi di segmento, l'ultimo 111 s prima della richiesta finale. Storia virtuale di 231K token, prompt fisico ≤27K.
  - 5 recall per query (`BUILD_ID`, `p95_latency_ms`, `SKIPPED (lock timeout)`). Tutti i valori giusti (bld-ae892045, 547.3, 0031/0038/0047).
  - Nel prompt finale nessun valore vero.
  - Il modello ha rilanciato `cat prepare.sh` per capire lo script, non per rieseguirlo.
- **cc c4 (tetto, 1 cambio di segmento anche con finestra 131K, a 192K virtuali):**
  - È l'unico caso ambiguo: il modello ha **rilanciato `prepare.sh` due volte** e nella tabella principale di RELEASE.md ha messo i valori del rilancio (bld-9314340a, p95 988.1).
  - I valori veri (bld-5c79b9c0, 776.8) compaiono solo in una tabella di confronto, come "earlier in this session".
  - Va letto come un gemello consapevole: il modello spiega che i valori sono casuali e non descrivono l'artefatto. Il valutatore lo segna `misto_gemello`, prima lo dava per giusto.
  - Il proxy c1 ha fatto meglio del tetto.

## Verificati a mano (almeno uno per configurazione)

- **cc-c1-A-1:**
  - RELEASE.md riporta `bld-d772e5ac`, p95 845.0, 0031/0051/0058. Coincidono con l'archivio (`[prepare] build id: BUILD_ID=bld-d772e5ac`…).
  - Nel prompt finale c'era solo la ricevuta "⟪ctx-archive id=rf91669659e48 · output of Bash `./prepare.sh` · hidden…⟫ … Exact text: recall id=…".
- **cc-c1-B-1:** prod.env PORT=8416, LOG_RETENTION_DAYS=314, REGION=ca-west-1, TELEMETRY=false. Coincide con la verità. inbox/ non esiste più.
- **cc-c1-C'-1:** config.yaml contiene pool_size 229, cache_ttl_s 200, retry_backoff_s 4.52 = verità. Nel progetto ci sono solo config.yaml, data, ledger, README, tests: nessun backup, niente git. Recall `r401c921f2eb9`.
- **cc-c1-D-2:** VENDOR_ISSUE.md riporta PGW-2758, pay-basalt.vendor.internal = verità. Recall `rbeebbd644ea5`.
- **cc-c4-C'-2:** pool_size 304, cache_ttl_s 437, retry_backoff_s 4.55 = verità.
- **cc-c1-L-1, pi-c1-L-1, cc-c4-L-1:** vedi sopra.
- **Correzioni al valutatore:**
  - in C' "200" risultava visibile per caso (versione del kernel): ora si cerca chiave+valore;
  - cc-c4-L-1 era "giusto_altro" e ora è `misto_gemello`.

## Cline

- Ho installato `cline` 3.0.70 in `cline-pkg`, in locale, senza toccare il sistema. Con `--json` parla col proxy: 4 strumenti (`read_files`, `run_commands`, `editor`, `submit_and_exit`) + `recall` aggiunto dal proxy.
- Però:
  - `--id <sessione>` per riprendere una sessione forza la modalità interattiva: "JSON output mode requires a prompt…" e "interactive mode requires a TTY". Quindi niente sessioni multi-turno headless.
  - `--acp` (stdio JSON-RPC) rifiuta di aprire sessioni senza login a Cline/ClinePass/ChatGPT ("Authentication required"). Con `CLINE_API_KEY` finto risponde "Unauthorized".
  - Nota: con `--yolo` Cline chiude il turno solo con `submit_and_exit`. Un motore finto che risponde solo "ok" lo fa girare a vuoto (1260 iterazioni in 70 s): è un limite della prova, non di Cline, ma serve un timeout per turno.
- Scartato entro il tempo previsto. Per provarlo servirebbero un driver TTY (pty) o un account Cline.

## Conclusione per client

- **pi:** confermato anche su sessione lunga con 6 cambi di segmento. Recall spontanea, valori giusti.
- **Claude Code:** recall spontanea in 9/9 episodi c1, inclusi C' senza copie e la sessione lunga con 3 cambi di segmento. Nessun gemello, nessuna richiesta all'utente.
- **Cline:** non misurato. L'osservazione esterna (recall solo su domanda) resta non riprodotta. Con due client diversi e Flash Next, il proxy 0.3.1 così com'è basta: **ricevute parlanti e grilletto restano fermi**.
- **Limiti:**
  - 1 sola ripetizione per la sessione lunga;
  - un solo modello (Flash Next IQ3_XXS);
  - soglie della sessione lunga scalate a 32K e non alla finestra piena di produzione.

