# RESULT — mnemonic-proxy 0.3.2: Windows nativo (card t_76051d7d)

Branch `feature/windows` su `origin` (maverde73/virtual-context-proxy), base `release/0.3.1` (d50b273).
Ultimo commit verificato: `c3d9640`. Niente push su `lastreload`, niente tag o release.

## Esito

Funziona su Windows nativo (runner `windows-latest`, CPU), davanti a `llama-server.exe` ufficiale b11430 con
`--slot-save-path .\slots`. Ultimo run completo, 6 job verdi su 6:
https://github.com/maverde73/virtual-context-proxy/actions/runs/38140673008

| job | esito |
|---|---|
| test (3.10), test (3.14) — Linux | verde |
| test-windows (3.10), test-windows (3.14) | verde: 245 test, demo con console cp1252, check contro fake engine (32K READY, 8K rifiutato) |
| llama-cpu — Linux, Qwen3-0.6B | verde, compreso state_e2e |
| llama-windows — llama-server.exe b11430 CPU + Qwen3-0.6B Q8_0 | verde: check --live READY, round trip chat, state_e2e PASS, start-windows.bat |

Log del job Windows reale: https://github.com/maverde73/virtual-context-proxy/actions/runs/38140673008/job/114473750002

Run precedenti (stesso codice, solo doc/CI cambiati dopo):
- 38140065397 (6238ae2): 6/6 verdi
- 38139276990 (cefc574): Windows verdi, llama-cpu rosso per "Illegal instruction" (vedi sotto, corretto)

Suite Linux in locale (Python 3.14 e 3.10 via uv): 245 test OK (6 saltati), 219 test OK su 3.10 (7 saltati), due
passate consecutive verdi. Una passata locale ha dato 1 errore che non si è ripresentato in tre passate successive:
non riprodotto.

## Tempi misurati su Windows (state_e2e, Qwen3-0.6B Q8_0, CPU del runner)

Conversazione di 3.2K token tramite il proxy → autosave in `slots` → riavvio di llama-server.exe → stesso turno:

| run | ripristino (motore) | turno dopo ripristino | stesso turno rileggendo (file nascosto) | token letti dopo ripristino |
|---|---|---|---|---|
| 38139276990 | 95 ms | 2.34 s | 35.71 s | 37 su 3174 |
| 38140065397 | — | — | 29.14 s | 37 su 3174 |
| 38140673008 | 68 ms | 2.43 s | 36.02 s | 37 su 3174 |

File di stato: 345.5 MB. `kv_archive` (Python 3.14, zstd): archivio 331 MB (rapporto 0.914), originale
cancellato, ricostruito in 1.1–2.4 s, ripristinato dal motore (3158 token) in 43–111 ms.

Stesso strumento su Linux in locale (5700G, 8 thread): ripristino 89 ms, turno 1.23 s contro 9.78 s.

## Modifiche (file:riga, rispetto a d50b273)

- `ctxproxy/compat.py` (nuovo): `lock_fd`/`unlock_fd` (r. 22–41: `msvcrt.locking` su 1 byte all'offset 0 su
  Windows, ripetuto finché concesso; `fcntl.flock` altrove), `console_safe` (r. 44: stdout/stderr con
  `errors="backslashreplace"` se la codifica non è UTF-8), `sqlite_ro_uri` (r. 56: `file:///C:/...` su Windows,
  invariato su POSIX), `replace` (r. 66: `os.replace`, su Windows riprova ~2.5 s su PermissionError), `O_BINARY`
  (r. 82), `bad_name` (r. 85: su Windows rifiuta anche `\ : * ? " < > |` e nomi che finiscono con spazio o punto).
- `ctxproxy/kvarchive.py`: tolto `import fcntl`; lock (r. 279, 284) via compat; `compat.replace` (r. 354, 455, 545);
  `O_BINARY` su `os.open` (r. 279, 535); controllo nome manifest via `compat.bad_name` (r. 269).
- `ctxproxy/server.py`: `compat.replace` per `last_request.json` (r. 491); `ConnectionError` invece di
  BrokenPipe/ConnectionReset (r. 336, 688: su Windows la disconnessione è `ConnectionAbortedError` WinError 10053);
  `compat.console_safe()` all'avvio (r. 754).
- `ctxproxy/mcp_server.py`: URI sola lettura via compat (r. 100); `console_safe(stderr)` (r. 372).
- `ctxproxy/fake_engine.py` r. 273: `ConnectionError` (fake engine conta le cancellazioni anche su Windows).
- `ctxproxy/check.py` r. 85, `ctxproxy/packtok.py` r. 20: `encoding="utf-8"` esplicito.
- `ctxproxy/demo.py` r. 101: `TemporaryDirectory(ignore_cleanup_errors=True)` (sqlite aperto su Windows).
- `tests/*.py`: `TemporaryDirectory(ignore_cleanup_errors=True)` (16 file; solo pulizia).
- `tests/test_compat.py` (nuovo, 124 righe): lock esclusivo (due fd, due thread), import di kvarchive senza
  fcntl, URI con spazi/`#`/`%`, replace, bad_name, stream cp1252.
- `tools/state_e2e.py` (nuovo): e2e dello stato salvato con llama-server vero, qualunque OS.
- `examples/start-windows.bat` (nuovo, CRLF, `.gitattributes`): engine + check + proxy; provato in CI.
- `.github/workflows/ci.yml`: job `test-windows` (3.10, 3.14) e `llama-windows` (zip b11430 sha256
  `b608455b…9666`, modello sha256 `361cc681…e1d` come Linux). Linux `llama-cpu`: build `GGML_NATIVE=OFF` + nuova
  chiave di cache (la build in cache era `-march=native` e su un runner con CPU diversa moriva con "Illegal
  instruction": difetto preesistente, emerso qui) e passo state_e2e.
- `README.md`: tabella "Saved state, measured" (riga Windows), Platforms → "Windows, native" con PowerShell, .bat,
  cosa è testato e cosa no; WSL resta come alternativa (ancora "Not yet tested"). Tests: state_e2e.
- `CHANGELOG.md`: voce 0.3.2 "unreleased". Versione in `pyproject.toml`/`__init__.py` lasciata 0.3.1: il bump è
  nella card figlia PyPI (t_a7ee3301).

Comportamento su Linux: invariato (compat su POSIX chiama esattamente le stesse funzioni di prima; l'unica differenza
è che `ConnectionAbortedError`/altre `ConnectionError` ora sono trattate come disconnessione del client).

## Audit: cose controllate e non cambiate

- `signal`: non usato nel pacchetto. `os.chmod`: solo in un test (funziona anche su Windows, sola lettura).
- `/` cablati: solo su percorsi HTTP o su percorsi di file *dentro i messaggi* del modello (recall), non su file locali.
- Nomi dei file di stato (`c…-seg0-auto-….bin`, `…-anchor1.bin`): nessun `:`.
- `slot_dir` vs `--slot-save-path`: il proxy non confronta stringhe; `check --live` verifica che il file salvato dal
  motore compaia in `slot_dir` (passato su Windows con `.\slots` e percorso `D:\...` assoluto).
- `os.uname()` in kvarchive (r. 242) è dentro un ramo Linux già protetto.

## Limiti residui

- Non testato: GPU (CUDA/Vulkan) su Windows reale, Windows desktop (solo runner CI), agenti veri (pi, Claude Code,
  Codex) su Windows, dashboard, WSL.
- Il caso guida (RTX 2060 6 GB, 131K, KV Q8, `-np 1`) non è riproducibile qui: nessuna GPU. Per 131K con KV Q8 il
  file di stato cresce in proporzione (≈345 MB per 3.2K token con 0.6B in F16: dipende dal modello).
- Il lock Windows (`msvcrt.locking` LK_LOCK) da solo riprova ~10 s e poi solleva errore; compat lo ripete finché
  non lo ottiene, quindi attende senza limite come `flock`. Il test (`tests/test_compat.py`, due fd sullo stesso
  file in due thread) passa su Windows CI; un test fra processi distinti non c'è.
- Un errore unitario locale isolato non riprodotto (vedi sopra).
