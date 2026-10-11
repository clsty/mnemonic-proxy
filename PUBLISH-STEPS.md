# Publishing mnemonic-proxy 0.3.2 on PyPI — steps for Maurizio

Everything up to the release is ready on `origin/feature/pypi` (maverde73/virtual-context-proxy). Nothing has been
pushed to `lastreload`, no tag, no release, nothing uploaded to PyPI or TestPyPI.

The names below must match EXACTLY what is registered on PyPI; do not rename them:
workflow file `.github/workflows/publish.yml`, GitHub environment `pypi`, repository `lastreload/mnemonic-proxy`.

## 1. PyPI account and pending Trusted Publisher — DONE (11/10 14:33)

- [x] PyPI account.
- [x] Pending Trusted Publisher on https://pypi.org/manage/account/publishing/ :
      project `mnemonic-proxy`, owner `lastreload`, repository `mnemonic-proxy`, workflow `publish.yml`,
      environment `pypi`.

## 2. GitHub environment `pypi` on lastreload/mnemonic-proxy — DONE

- [x] Settings → Environments → `pypi` exists.
- [ ] Optional (recommended): in that environment add yourself under "Required reviewers", so every publish waits
      for one click of approval; and "Deployment branches and tags" → selected tags `v*`.

## 3. Merge into lastreload/main

`feature/pypi` = `feature/windows` (0.3.2 Windows support) + lastreload/main (PR #2, already merged in) + the PyPI
packaging. From the local repo:

```sh
cd ~/src/virtual-context-proxy
git fetch origin lastreload
git checkout -B pub-main lastreload/main
git merge --ff-only origin/feature/pypi        # fast-forward: feature/pypi already contains lastreload/main
git push lastreload pub-main:main
```

(If `lastreload/main` moved in the meantime, the fast-forward fails: merge `lastreload/main` into `feature/pypi`
first, re-run CI, then retry. Alternatively open a PR feature/pypi → lastreload/main on GitHub and merge it there.)

Optional, before the release: remove `RESULT.md` and `PUBLISH-STEPS.md` from main (worker notes with local paths;
they are not in the wheel/sdist either way), and change `## 0.3.2 — unreleased` in CHANGELOG.md to `## 0.3.2 — <date>`.

Wait for the `ci` run on lastreload/main to be green (Actions tab).

## 4. Release v0.3.2 → the workflow publishes

On GitHub: lastreload/mnemonic-proxy → Releases → Draft a new release → tag `v0.3.2` (create on `main`), title
`v0.3.2`, notes = the 0.3.2 section of CHANGELOG.md (it already thanks @erycsonero for PR #2: keep the `@`, GitHub
notifies him) → **Publish release**. Or from the shell:

```sh
gh release create v0.3.2 -R lastreload/mnemonic-proxy --target main --title v0.3.2 --notes-file <notes.md>
```

The `publish` workflow starts on "release published":
- job `build`: checks that the tag is `v` + the version in `pyproject.toml` and `ctxproxy/__init__.py` (0.3.2; it
  stops otherwise), builds sdist + wheel, `twine check --strict`, installs the wheel in a clean venv and runs
  `mnemonic-proxy demo`;
- job `pypi` (environment `pypi`, OIDC, no token): uploads with `pypa/gh-action-pypi-publish`. If you set required
  reviewers, approve it under Actions → the run → Review deployments.

The first successful upload turns the pending publisher into the real project `mnemonic-proxy`.

## 5. Verify

```sh
python3 -m venv /tmp/mp && /tmp/mp/bin/pip install mnemonic-proxy==0.3.2
cd /tmp && /tmp/mp/bin/mnemonic-proxy demo          # ends with PASS
uvx mnemonic-proxy demo                             # if uv is installed
```

and look at https://pypi.org/project/mnemonic-proxy/ (images, links, classifiers). Windows: `py -m venv v;
v\Scripts\pip install mnemonic-proxy==0.3.2; v\Scripts\mnemonic-proxy demo`.

If a release is ever wrong: on PyPI a version cannot be re-uploaded; "yank" it and release 0.3.3.

## 6. Social preview (GitHub)

lastreload/mnemonic-proxy → Settings → General → Social preview → Edit → Upload an image →
`docs/assets/social-preview.png` (1280×640, the hero image already cropped; in the repo after the merge, or from
`~/src/vcp-wt/pypi/docs/assets/social-preview.png`).
