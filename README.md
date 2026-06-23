```

    _/_/_/_/    _/_/    _/    _/  _/_/_/_/
   _/        _/    _/  _/  _/    _/
  _/_/_/    _/_/_/_/  _/_/      _/_/_/
 _/        _/    _/  _/  _/    _/
_/        _/    _/  _/    _/  _/_/_/_/

```

*Fake* is a Python module that generates fake data, with the following features:

- Covers names, addresses, emails, time and dates, words, titles and paragraphs
- Can anonymize nested JSON payloads by guessing field types and fuzzing values (including optional redaction of secrets/passwords/tokens)
- Produces the same datasets given the same seed `fake.seed(n)`.

It also ships with a standalone JavaScript module in `src/js/fake.js` that can
fetch the datasets directly from GitHub.

Fake is also very easy to extend: simply drop a new data file in `src/py/fake/data`,
register the JSON file in `Data.DATASETS` and add a top-level function to
use it.

# Install

```
python3.14 -m pip install --user fake-data
```

# CLI

The package also installs a `fake` command:

```
fake [params] TYPE [params] [COUNT]
fake anon -s SEED [-d mapping.json] [--redact-secrets] DATA.json
fake redact -s SEED [-d mapping.json] DATA.json
fake deanon -s SEED -d mapping.json DATA.json
```

- `-s`, `--seed` seeds the fake data generator
- `-d`, `--dict` reads or writes the reusable anon/deanon mapping JSON
- `-f`, `--format=text|json` selects line-based text or JSON output
- `TYPE` is any top-level generator from the `fake` module, like `name`, `email`, `text` or `date`
- `COUNT` defaults to `1` and can also be a range like `100-10000`, in which case the CLI picks a random count independently from `--seed`
- `anon` / `redact` anonymizes a JSON file (with optional `--redact-secrets` for passwords/tokens/API keys) and writes to stdout
- `deanon` restores an anonymized JSON file with the same `--seed` and a mapping file
- anon/deanon default to a fixed seed of `0` when `--seed` is omitted
- If `TYPE` is a JSON file path, the CLI anonymizes it and writes the anonymized JSON to stdout

Examples:

```
fake name
fake --seed 42 email 5
fake --format json city 10
fake text --lang=fr --length=long --words-per-line=3-10
fake name --male 3
fake name --no-male --female
fake anonymize payload.json
fake redact --seed 42 payload.json
fake anon --seed 42 --redact-secrets --dict mapping.json payload.json
fake deanon --seed 42 --dict mapping.json payload.anonymized.json
fake anon --dict mapping.json payload.json
fake deanon --dict mapping.json payload.anonymized.json
```

# JavaScript

The JavaScript module is ESM-only. It can be dropped into a project directly or loaded from a CDN/GitHub.

**From CDN (recommended):**

```js
import fake from "https://cdn.jsdelivr.net/gh/sebastien/fake@main/src/js/fake.js";

await fake.preload();
fake.seed(1);

console.log(fake.name());
console.log(fake.email());
console.log(fake.title());
console.log(await fake.redact({ password: "hunter2", apiKey: "sk_live_xxx" }));
```

**Or from local file:**

```js
import fake from "./src/js/fake.js";
```

The JavaScript API mirrors the Python top-level API after `await fake.preload()`.
Datasets are fetched with `fetch()` from GitHub (via CDN or raw URL). In Bun they are cached locally.

In Bun, fetched datasets are also cached locally in `.cache/fake/*.json`.

If you want to override the dataset source, pass custom base URLs to `preload()`:

```js
await fake.preload({
  baseUrls: [
    "https://cdn.jsdelivr.net/gh/sebastien/fake@main/src/py/fake/data/",
    "https://raw.githubusercontent.com/sebastien/fake/main/src/py/fake/data/"
  ]
});
```

# Testing

Feature coverage for anonymization lives in `tests/` and uses shared JSON fixtures
under `tests/data/` across Python and JavaScript.

- `tests/anonymize_test.py` runs with `unittest`
- `tests/anonymize.test.js` runs with Bun
- `tests/data/*.json` contains hand-written, industry-generic anonymization payloads

Run both suites with:

```sh
make test
```

Run a single suite with:

```sh
make anonymize-py-test
make anonymize-js-test
```

# Generators

## Personal information

The `name` and `firstName` take `(male=True|False,female=True|False)` so
that you can select whether you want a male `(male=True)` or female `(female=True)`
name.

- `fake.name()`:      Josh Benson
- `fake.firstName()`: Leticia
- `fake.lastName()`:  Potts
- `fake.user()`:      dip_johnedward11
- `fake.email()`:     golfnduo@sohu.com
- `fake.phone()`:     +5 (645)-108103-18810
- `fake.zip()`:       75193
- `fake.address()`:   5832, Midcrest Way
- `fake.city()`:      Qianping
- `fake.country()`:   Nepal
- `fake.company()`:   United Holdings Inc.

## Time & Dates

- `fake.day()`:     Saturday
- `fake.month()`:   December
- `fake.seconds()`: 32
- `fake.hour()`:    01:02
- `fake.now()`:     2017-12-26 09:37:54.113547
- `fake.number()`:  32
- `fake.date()`:    2017-12-26 09:37:54.113609

## Text

- `fake.word()`: since
- `fake.text()`: Concubines aisle cheer cushioned transitorie befell at soon‥
- `fake.title()`: Dalla morrow dalla alas not evermore lineage through‥
- `fake.paragraph()`: Strength aye accio feather into amiss. Blazon alone uncouth disaster‥
- `fake.topic()`: Bird

# Anonymize / Redact Secrets

`fake.anonymize(payload, seed=None, variance=0.25, hints=None, mapping=None, redact_secrets=False)`
(and alias `fake.fuzz()`) walks a JSON-like payload, guesses likely field types from key names and value
patterns (including high-entropy secrets, passwords, tokens, API keys), and returns both the anonymized payload and a
minimal reusable reverse mapping.

Use `fake.redact(payload, ...)` or `redact_secrets=True` to enable secret redaction (replaces with `[REDACTED-SECRET-...]`
and adds `"secrets": true` to the mapping so it can be stored securely).

```python
import fake

fake.seed(42)
result = fake.anonymize({
  "customer": {
    "name": "Alice Martin",
    "email": "alice@example.com",
    "password": "hunter2",
    "apiKey": "sk_live_9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c"
  },
  "amount": 1200.50
}, seed=42, redact_secrets=True)

print(result["value"])
print(result["mapping"])

original = fake.deanonymize(result["value"], seed=42, mapping=result["mapping"])
print(original)
```

Unknown strings are left unchanged by default, except when they contain values
that were anonymized elsewhere in the payload. `fake.fuzz(...)` is an alias for
`fake.anonymize(...)`.

With the same payload and the same seed, anonymization is reproducible. The
reverse mapping only keeps entries for string-like values that cannot be
recovered algorithmically, so numeric, date, datetime and phone transforms do
not grow the mapping.
