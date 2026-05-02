# AGENTS Notes

## Repo shape
- Single Python package: `fake` under `src/py/fake`; public API is mostly top-level functions in `src/py/fake/__init__.py`.
- Data-driven generators read JSON files in `src/py/fake/data/*.json`; if behavior changes, check dataset contents first.

## Verified dev commands
- Install for local usage: `python3.14 -m pip install --user fake-data` (from `README.md`).
- Run quick smoke output: `PYTHONPATH=src/py python test.py`.
- Regenerate topics dataset only: `make src/py/fake/data/topics.json` (builds from `src/py/fake/text/topics.txt`).

## Test and verification reality
- There is no `tests/` directory in this repo, even though `Makefile` has legacy `test`/`tests` targets pointing to missing files.
- Prefer focused checks via direct module import or `test.py` instead of `make test`.

## Packaging/tooling quirks
- Packaging now uses `pyproject.toml` + `setuptools.build_meta`; use `python -m build` for a modern package check.
- `setup.py` reads `VERSION` from `src/py/fake/__init__.py`; keep the assignment format (`VERSION = "..."`) simple.
- `MANIFEST.in` explicitly lists packaged JSON data files; if adding a new dataset, update both `Data.DATASETS` and packaging inclusion.

## Editing guidance for this codebase
- Keep `PYTHONPATH=src/py` when running scripts from repo root so `import fake` resolves.
- Preserve existing naming style for public API (`firstName`, `lastName`, etc.) unless doing a deliberate breaking-change migration.
