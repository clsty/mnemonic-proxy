# RESULT — mnemonic-proxy 0.3.2 su PyPI (card t_a7ee3301)

Branch `feature/pypi` su `origin` (maverde73/virtual-context-proxy), worktree `~/src/vcp-wt/pypi`, base
`feature/windows` (0503591) + merge di `lastreload/main` (PR #2, finestra di contesto da Strata: senza, il merge su
lastreload/main non sarebbe stato fast-forward). Niente push su `lastreload`, niente tag, release o upload.
Il report della card Windows (t_76051d7d) è in `~/src/vcp-wt/windows/RESULT.md` e nella storia git.

Nome `mnemonic-proxy` su PyPI ricontrollato all'inizio: `https://pypi.org/pypi/mnemonic-proxy/json` → 404 (libero;
pending publisher già registrato da Maurizio).

## File cambiati (rispetto a feature/windows)

- `pyproject.toml`: versione 0.3.2; `license = "MIT"` (SPDX) + `license-files`; `readme` con content-type
  markdown; classifiers: Development Status 4 Beta, Environment Console, Intended Audience Developers,
  POSIX Linux, **Microsoft Windows** (CI Windows verde in t_76051d7d e qui), Python 3.10/3.11/3.12/3.13/3.14,
  Topic AI / Software Development / Proxy Servers; URL Changelog e Issues; `setuptools>=77` (serve per la licenza SPDX).
  Codice invariato.
- `ctxproxy/__init__.py`: `__version__ = "0.3.2"` (coincide con pyproject; publish.yml lo verifica contro il tag).
- `README.md`: immagini → `raw.githubusercontent.com/lastreload/mnemonic-proxy/main/docs/assets/...` (5),
  link relativi (docs/dev-notes, examples, LICENSE) → `github.com/lastreload/mnemonic-proxy/blob/main/...` (12),
  verificato che non ne restano di relativi; installazione T0 e Windows: `pip install mnemonic-proxy`, più
  `uvx mnemonic-proxy demo` e `git+https://...` come versione di sviluppo; `[exact]` senza git; "git" tolto dai
  prerequisiti di T0; "AI395:" → "Hardware:" (nome host, finiva nel METADATA del wheel).
- `docs/index.html`: `pip install mnemonic-proxy` (# or: uvx mnemonic-proxy demo).
- `CHANGELOG.md` 0.3.2: voce "Available on PyPI"; tolta la nota "versione ancora 0.3.1".
- `.github/workflows/publish.yml` (nuovo): su `release: published`; job `build` (tag == v+versione, build,
  `twine check --strict`, wheel installato in venv pulito + demo, artifact) → job `pypi` con environment `pypi`,
  `permissions: id-token: write`, `pypa/gh-action-pypi-publish@release/v1`. Nessun segreto.
- `.github/workflows/ci.yml`: job `package` (build + twine check + elenco wheel) e `package-install`
  (ubuntu-24.04 e windows-latest × Python 3.10/3.14: pip install del wheel in venv pulito, `mnemonic-proxy demo`
  → PASS, `mnemonic-mcp --help`, `uvx --from <wheel> mnemonic-proxy demo` → PASS).
- `docs/assets/social-preview.png` (nuovo): hero 1344×768 ridimensionato a 1280 di larghezza e ritagliato al
  centro a 1280×640 (nessun testo/logo nell'immagine, si perdono solo i bordi alto/basso).
- `PUBLISH-STEPS.md` (nuovo): passi per Maurizio. `RESULT.md`: questo file (sostituisce quello della card Windows).
- Dal merge di lastreload/main: `ctxproxy/engines.py`, `ctxproxy/fake_engine.py`, `tests/test_engines.py` (PR #2).

## Artefatti (build locale, Python 3.14, `python -m build`)

| file | sha256 |
|---|---|
| `mnemonic_proxy-0.3.2-py3-none-any.whl` (161 KB) | `02519e408bb0767019f844a6d545bf6403eac73d72485af3d52c3d7db0a528d2` |
| `mnemonic_proxy-0.3.2.tar.gz` (242 KB) | `cb0866c03b5b8c3ada8cd41f66a0bd0e13c9b713e70a32ed7a5128abb01a4e13` |

(In `~/src/vcp-wt/pypi/dist/`, build del commit f2f791c. Non sono i file che verranno pubblicati: publish.yml
ricostruisce dal tag; gli hash possono differire per timestamp e per i file .md cambiati dopo.)
`twine check --strict`: PASSED su entrambi.

Contenuto del wheel: `ctxproxy/` (`__init__`, api_anthropic, api_responses, autosave, check, compat, core, demo,
engines, fake_engine, kvarchive, lang, mcp_server, packtok, paging, recall2, render, server, tooldefs, upstream) +
`dist-info` (METADATA, WHEEL, entry_points: mnemonic-proxy, ctxproxy, mnemonic-mcp; licenses/LICENSE; RECORD;
top_level). Niente dev-notes, bench, tools, dashboard, dati.
sdist: lo stesso + README, LICENSE, pyproject, `tests/` (test unitari, senza dati).
Grep su wheel e sdist estratti per `mverde`, `/mnt/`, `PC4070TI`, `AI395`, `MVLINNA`, `10.77.`, `/home/`: nessuna
occorrenza.

## Installazione dal wheel

| piattaforma | Python | pip install wheel | `mnemonic-proxy demo` | `mnemonic-mcp --help` | uvx --from wheel |
|---|---|---|---|---|---|
| Linux locale (uv venv pulito) | 3.10.21 | ok (0.3.2) | PASS 0.6 s | ok | — |
| Linux locale | 3.14.7 | ok (0.3.2) | PASS 0.6 s | ok | PASS |
| CI ubuntu-24.04 | 3.10 / 3.14 | ok | PASS | ok | PASS |
| CI windows-latest (console cp1252) | 3.10 / 3.14 | ok | PASS (1.8 s su 3.14) | ok | PASS (2.2 s) |

## Test

- Locale: `python -m unittest discover -s tests -t .` → Python 3.14: 246 OK (6 skip); Python 3.10: 220 OK (7 skip).
- CI su `origin` branch `feature/pypi`, commit f2f791c, workflow_dispatch con llama=true: tutti gli 11 job verdi
  (test 3.10/3.14, test-windows 3.10/3.14, llama-cpu, llama-windows, package, package-install ×4):
  https://github.com/maverde73/virtual-context-proxy/actions/runs/38141882299
  (il run da push 38141868901 è stato annullato dalla concurrency quando è partito il dispatch: stesso commit.)
  Commit successivi: solo PUBLISH-STEPS.md e RESULT.md (il push fa ripartire la CI: vedi link nel commento card).
- `publish.yml` non è eseguibile senza release: verificato solo che il YAML è valido (trigger release/published,
  job build → pypi). Il suo job build ripete gli stessi passi già verdi nel job `package` di CI.

## Cosa resta a Maurizio (dettagli in PUBLISH-STEPS.md)

1. (fatti) account PyPI, pending Trusted Publisher, environment `pypi` su lastreload/mnemonic-proxy.
2. Merge `feature/pypi` su lastreload/main (fast-forward).
3. Release `v0.3.2` su GitHub → `publish.yml` pubblica.
4. Verifica `pip install mnemonic-proxy==0.3.2` in venv pulito.
5. Social preview: caricare `docs/assets/social-preview.png`.
