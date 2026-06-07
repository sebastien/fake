```
                                             
    _/_/_/_/    _/_/    _/    _/  _/_/_/_/   
   _/        _/    _/  _/  _/    _/          
  _/_/_/    _/_/_/_/  _/_/      _/_/_/       
 _/        _/    _/  _/  _/    _/            
_/        _/    _/  _/    _/  _/_/_/_/       
                                             
```

*Fake* is a Python module that generates fake data, with the following features:

- Covers names, addresses, emails, time and dates, words, titles and paragraphs
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
```

- `-s`, `--seed` seeds the fake data generator
- `-f`, `--format=text|json` selects line-based text or JSON output
- `TYPE` is any top-level generator from the `fake` module, like `name`, `email`, `text` or `date`
- `COUNT` defaults to `1` and can also be a range like `100-10000`, in which case the CLI picks a random count independently from `--seed`

Examples:

```
fake name
fake --seed 42 email 5
fake --format json city 10
fake text --lang=fr --length=long --words-per-line=3-10
fake name --male 3
fake name --no-male --female
```

# JavaScript

The JavaScript module is ESM-only and is designed to be dropped into another
project directly.

```js
import fake from "./src/js/fake.js";

await fake.preload();
fake.seed(1);

console.log(fake.name());
console.log(fake.email());
console.log(fake.title());
```

The JavaScript API mirrors the Python top-level API after `await fake.preload()`.
Datasets are fetched with `fetch()` from GitHub using a CDN or raw GitHub URL.

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
- `fake.company()`:   Kinder Morgan, Inc.

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
