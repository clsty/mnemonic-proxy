# Author: Maurizio Verde — LastReload
"""Saved-state end to end with a real llama-server, on any OS (written for the windows-latest CI runner).

    python tools/state_e2e.py --server PATH/llama-server[.exe] --model model.gguf --work DIR [--kv-archive]

1. starts llama-server (-c 32768 --parallel 1 --jinja --slot-save-path DIR\\slots) and mnemonic-proxy in front,
   with autosave on (short idle, low thresholds so a ~4K-token conversation qualifies);
2. a long first turn through the proxy (cold read, timed by the engine), then waits for the proxy's autosave file;
3. kills and restarts llama-server (its KV cache is gone), sends the next turn through the proxy: the proxy must
   restore the autosave from disk (journal event `autorestore`) and the engine must read only the new suffix;
4. restarts llama-server again and sends the same second turn straight to the engine (no proxy, no restore): the
   re-read baseline;
5. with --kv-archive (Python >= 3.14): the autosave file is archived (zstd blocks, sha256), deleted, rebuilt from the
   archive and restored by the engine.
Writes DIR/state_e2e.json with the timings; exit 1 on any failed assertion.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def http(method, url, body=None, timeout=900):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"null")


def wait_health(url, secs=180):
    t = time.time()
    while time.time() - t < secs:
        try:
            http("GET", url + "/health", timeout=5)
            return
        except (urllib.error.URLError, OSError, ValueError):
            time.sleep(0.5)
    raise SystemExit("not healthy after %ds: %s" % (secs, url))


def document(n_sections=40):
    """~4K tokens of deterministic text with one fact to look up."""
    words = ("cache slot prefix token window segment archive handoff receipt recall engine restore save "
             "kernel thread queue batch shard layer vector anchor").split()
    out = []
    for i in range(n_sections):
        line = " ".join(words[(i * 7 + j * 3) % len(words)] for j in range(60))
        out.append("Section %d. %s." % (i + 1, line))
        if i == 27:
            out.append("Note: the build id of the release candidate is RC-7741-WIN.")
    return "\n".join(out)


class Engine:
    def __init__(self, a, slots, port):
        self.cmd = [a.server, "-m", a.model, "-c", "32768", "--parallel", "1", "--jinja", "--slot-save-path", slots,
                    "--port", str(port), "--host", "127.0.0.1", "-t", str(a.threads)]
        self.url = "http://127.0.0.1:%d" % port
        self.log_path = os.path.join(a.work, "engine.log")
        self.p = None

    def start(self):
        log = open(self.log_path, "ab")
        self.p = subprocess.Popen(self.cmd, stdout=log, stderr=subprocess.STDOUT)
        log.close()
        wait_health(self.url)

    def stop(self):
        if self.p and self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(30)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(30)


def journal(data, event):
    path = os.path.join(data, "journal.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [e for e in (json.loads(x) for x in f if x.strip()) if e.get("event") == event]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--kv-archive", action="store_true")
    ap.add_argument("--port", type=int, default=18295, help="engine port; the proxy listens on port + 1")
    a = ap.parse_args(argv)
    a.work = os.path.abspath(a.work)
    a.server, a.model = os.path.abspath(a.server), os.path.abspath(a.model)
    slots, data = os.path.join(a.work, "slots"), os.path.join(a.work, "data")
    os.makedirs(slots, exist_ok=True)
    os.makedirs(data, exist_ok=True)
    cfg = {"slot_dir": slots, "slot_save": True, "mask_anchor": True, "autosave": True, "autosave_idle_s": 2,
           "autosave_poll_s": 1, "autosave_min_tokens": 1024, "autosave_min_free_gb": 1, "autorestore_min_gain": 1024,
           "mask_tool_args": True, "engine_tokenize": True}
    cfg_path = os.path.join(a.work, "cfg.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=1)
    eng = Engine(a, slots, a.port)
    proxy_url = "http://127.0.0.1:%d" % (a.port + 1)
    res = {"platform": sys.platform, "python": sys.version.split()[0], "slot_dir": slots, "checks": {}}
    fails = []

    def check(name, ok, detail=""):
        res["checks"][name] = {"ok": bool(ok), "detail": detail}
        print("[%s] %s %s" % ("ok" if ok else "FAIL", name, detail), flush=True)
        if not ok:
            fails.append(name)

    proxy = None
    try:
        eng.start()
        plog = open(os.path.join(a.work, "proxy.log"), "ab")
        proxy = subprocess.Popen([sys.executable, "-m", "ctxproxy.server", "--upstream", eng.url, "--port",
                                  str(a.port + 1),
                                  "--data", data, "--config", cfg_path], stdout=plog, stderr=subprocess.STDOUT,
                                 cwd=a.work)
        plog.close()
        wait_health(proxy_url, 60)
        msgs = [{"role": "system", "content": "You are a concise assistant. Answer in one short sentence."},
                {"role": "user", "content": "Read this document.\n\n" + document()
                 + "\n\nWhat is the build id of the release candidate? /no_think"}]
        body = {"model": "m", "max_tokens": 48, "temperature": 0, "messages": msgs}

        # 1. cold first turn through the proxy
        t0 = time.time()
        r1 = http("POST", proxy_url + "/v1/chat/completions", body)
        wall1 = time.time() - t0
        tm1 = r1.get("timings") or {}
        u1 = r1.get("usage") or {}
        res["turn1"] = {"prompt_tokens": u1.get("prompt_tokens"), "prompt_read": tm1.get("prompt_n"),
                        "prompt_ms": tm1.get("prompt_ms"), "wall_s": round(wall1, 2),
                        "reply": (r1["choices"][0]["message"].get("content") or "")[:200]}
        check("turn 1 through the proxy", u1.get("prompt_tokens", 0) >= 2048, json.dumps(res["turn1"]))

        # 2. autosave file written by the engine into slot_dir
        t0 = time.time()
        saves = []
        while time.time() - t0 < 120 and not saves:
            time.sleep(1)
            saves = journal(data, "autosave")
        fn = saves[-1]["file"] if saves else None
        path = os.path.join(slots, fn) if fn else ""
        res["autosave"] = {"file": fn, "ms": saves[-1].get("ms") if saves else None,
                           "bytes": os.path.getsize(path) if path and os.path.exists(path) else None,
                           "tokens": saves[-1].get("tokens") if saves else None}
        check("autosave file in slot_dir", bool(path) and os.path.exists(path), json.dumps(res["autosave"]))

        msgs2 = msgs + [{"role": "assistant", "content": r1["choices"][0]["message"].get("content") or ""},
                        {"role": "user", "content": "Repeat the build id only. /no_think"}]
        body2 = {**body, "messages": msgs2}

        # 3. engine restart: the proxy restores the autosave, the engine reads only the suffix
        eng.stop()
        eng.start()
        n_before = len(journal(data, "autorestore"))
        t0 = time.time()
        r2 = http("POST", proxy_url + "/v1/chat/completions", body2)
        wall2 = time.time() - t0
        tm2, u2 = r2.get("timings") or {}, r2.get("usage") or {}
        ar = journal(data, "autorestore")[n_before:]
        res["turn2_restored"] = {"autorestore": ar[-1] if ar else None, "prompt_tokens": u2.get("prompt_tokens"),
                                 "prompt_read": tm2.get("prompt_n"), "prompt_ms": tm2.get("prompt_ms"),
                                 "wall_s": round(wall2, 2),
                                 "reply": (r2["choices"][0]["message"].get("content") or "")[:200]}
        check("autorestore after engine restart", bool(ar) and ar[-1].get("file") == fn,
              json.dumps(res["turn2_restored"]))
        read2 = tm2.get("prompt_n") or 0
        check("engine read only the new suffix", 0 < read2 < 0.2 * (u2.get("prompt_tokens") or 1),
              "read %s of %s tokens" % (read2, u2.get("prompt_tokens")))

        # 4. baseline: restart again and send the same turn through the proxy with the state file hidden, so the
        #    restore cannot happen and the engine re-reads the very same physical prompt
        eng.stop()
        eng.start()
        hidden = path + ".hidden"
        os.replace(path, hidden)
        t0 = time.time()
        r3 = http("POST", proxy_url + "/v1/chat/completions", body2)
        wall3 = time.time() - t0
        os.replace(hidden, path)
        tm3, u3 = r3.get("timings") or {}, r3.get("usage") or {}
        res["turn2_reread"] = {"prompt_tokens": u3.get("prompt_tokens"), "prompt_read": tm3.get("prompt_n"),
                               "prompt_ms": tm3.get("prompt_ms"), "wall_s": round(wall3, 2)}
        check("re-read baseline (same prompt, no state file)",
              (tm3.get("prompt_n") or 0) >= 0.9 * (u2.get("prompt_tokens") or 1), json.dumps(res["turn2_reread"]))
        rest = ar[-1] if ar else {}
        res["summary"] = {"tokens": u3.get("prompt_tokens"),
                          "restore_ms_engine": rest.get("restore_ms"), "restore_ms_proxy": rest.get("ms"),
                          "turn_wall_s_restored": round(wall2, 2), "turn_wall_s_reread": round(wall3, 2),
                          "prompt_ms_reread": tm3.get("prompt_ms"),
                          "state_file_mb": round((res["autosave"]["bytes"] or 0) / 2 ** 20, 1)}

        # 5. kv_archive: archive the autosave, delete it, rebuild it, restore it in the engine
        if a.kv_archive and fn:
            from ctxproxy.kvarchive import KvArchive
            arc = KvArchive(os.path.join(a.work, "kv-archive"), threads=4)
            src_size = os.path.getsize(path)
            ra = arc.archive(path, fn, delete_original=True)
            gone = not os.path.exists(path)
            rr = arc.restore(fn, path)
            t0 = time.time()
            rs = http("POST", eng.url + "/slots/0?action=restore", {"filename": fn})
            res["kv_archive"] = {"bytes": src_size, "stored_bytes": ra["new_stored_bytes"],
                                 "ratio": round(ra["new_stored_bytes"] / max(1, src_size), 3),
                                 "archive_ms": ra["ms"], "rebuild_ms": rr["ms"], "deleted_original": gone,
                                 "engine_restore_ms": (rs.get("timings") or {}).get("restore_ms"),
                                 "n_restored": rs.get("n_restored"), "wall_restore_s": round(time.time() - t0, 2)}
            check("kv_archive round trip (archive, delete, rebuild, engine restore)",
                  gone and rr["bytes"] == src_size and (rs.get("n_restored") or 0) >= (res["autosave"]["tokens"] or 1),
                  json.dumps(res["kv_archive"]))
    except Exception as e:  # noqa: BLE001
        check("no exception", False, repr(e)[:500])
    finally:
        if proxy is not None and proxy.poll() is None:
            proxy.terminate()
            try:
                proxy.wait(30)
            except subprocess.TimeoutExpired:
                proxy.kill()
        eng.stop()
    res["ok"] = not fails
    with open(os.path.join(a.work, "state_e2e.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res.get("summary"), indent=1))
    print("PASS" if not fails else "FAIL: " + ", ".join(fails), flush=True)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
