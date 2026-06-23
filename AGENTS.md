
Fake is a library/tool to generate fake data, anonymse and redact existing data. It has:
- Data-driven generators read JSON files in `src/py/fake/data/*.json`

## Sources
- Python is authoritative/reference: src/py/fake
- JavaScript is the idempotent reimplementation: src/js/fake
- Convention is camelCase
- Reference data is in: src/py/fake/data

## Workflow
- `.appenv` to setup environment (load with `appenv` command)
- `make check` for errors, `make fmt` for formatting
- `make test` for testing

