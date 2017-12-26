```
                                             
    _/_/_/_/    _/_/    _/    _/  _/_/_/_/   
   _/        _/    _/  _/  _/    _/          
  _/_/_/    _/_/_/_/  _/_/      _/_/_/       
 _/        _/    _/  _/  _/    _/            
_/        _/    _/  _/    _/  _/_/_/_/       
                                             
```

*Fake* is a Python module that generates fake data, with the following features:

- Covers names, addresses, emails, time and dates, words, titles and paragraphs
- Produces reproductible datasets given the same seed `fake.seed(n)`.

Fake is also very easy to extend: simply drop a new data file in `src/fake/data`,
register the JSON file in `Data.DATASETS` and add a top-level function to 
use it.

# Install

```
pip install --user fake
```

# Generators

## Personal information

- `fake.name()`:      Josh Benson
- `fake.user()`:      dip_johnedward11
- `fake.email()`:     golfnduo@sohu.com
- `fake.phone()`:     +5 (645)-108103-18810
- `fake.zip()`:       75193
- `fake.address()`:   5832, Midcrest Way
- `fake.city()`:      Qianping
- `fake.country()`:   Nepal

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
