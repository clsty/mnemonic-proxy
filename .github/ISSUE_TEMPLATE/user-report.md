---
name: User report
about: Share numbers from running mnemonic-proxy on your own hardware
title: "User report: <GPU> / <model> / <client>"
labels: user-report
---

Thanks for sharing. Rough numbers are fine; say what you measured and what you estimated.
Before pasting anything from `data/journal.jsonl` or `data/archive.sqlite`, check it: they contain your prompts,
file contents and recall queries.

**Hardware** (GPU + VRAM, CPU, RAM):

**Engine and version** (Strata / llama-server / ds4-server / …, flags such as `--ctx`, `--slot-save-path`):

**Model and quantization:**

**Client** (Claude Code / Codex / Cline / OpenCode / pi / …, version, any compaction setting you changed):

**mnemonic-proxy version / commit:**

**Session**
- duration:
- total history (tokens):
- tokens in the last request:
- segment switches:

**Saved state** (tokens restored, time; re-read time if you know it):

**Recall**
- number of `recall` calls:
- how many the model made on its own vs. after you asked about the past:
- were the results used / correct?

**Anything that went wrong or felt slow:**

May we quote these numbers in the README (with your handle and hardware)? yes / no
