# Hash-pinned CI dependencies

CI and the release workflow install exact, hash-checked versions (OpenSSF Scorecard
"Pinned-Dependencies"). Lionstone itself is installed with `--no-deps` on top.
Dependabot keeps these files up to date. To regenerate them by hand:

```bash
uv pip compile pyproject.toml --extra dev --extra mcp --universal --python-version 3.10 --generate-hashes -o .github/requirements/ci.txt
uv pip compile .github/requirements/build.in --universal --python-version 3.10 --generate-hashes -o .github/requirements/build.txt
```
