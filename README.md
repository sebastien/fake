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

Fake is also very easy to extend: simply drop a new data file in `src/fake/data`,
register the JSON file in `Data.DATASETS` and add a top-level function to 
use it.

# Install

```
pip install --user fake-data
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
