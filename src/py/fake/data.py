# encoding: utf-8
# -----------------------------------------------------------------------------
# Project   : Fake
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : Revised BSD License                              © FFunction, inc
# -----------------------------------------------------------------------------
# Creation  : 2012-07-31
# Last mod  : 2018-04-09
# -----------------------------------------------------------------------------

import os
import json
import re
import random
import datetime

__doc__ = """
Allows to easily generate fake text and data.
"""

VERSION    = "0.9.1"
ROOT_PATH  = os.path.dirname(__file__)
DATA_PATH  = os.path.join(ROOT_PATH, "data")
DEFAULT_ANONYMIZE_SEED = 0
CURRENT_SEED = None

# -----------------------------------------------------------------------------
#
# DATA
#
# -----------------------------------------------------------------------------

class Data:
	"""Lazily loads datasets defined in DATASETS, where the dataset's key
	is bound to a dynamically assigned property."""

	DATASETS   = {
		"countries"        : "countries.json",
		"cities"           : "cities.json",
		"users"            : "users.json",
		"domains"          : "domains.json",
		"lastNames"        : "lastnames.json",
		"maleFirstNames"   : "firstnames-male.json",
		"femaleFirstNames" : "firstnames-female.json",
		"words"            : "words.json",
		"streets"          : "streets.json",
		"companies"        : "companies.json",
		"topics"           : "topics.json",
	}

	def __init__( self ):
		self.data = {}

	def _load( self, dataset ):
		if dataset not in self.data:
			path = os.path.join(DATA_PATH, self.DATASETS[dataset])
			with open(path) as f:
				self.data[dataset] = json.load(f)
		return self.data[dataset]

	def __getattr__( self, name ):
		if name in self.DATASETS:
			return self._load(name)
		else:
			return self.__dict__[name]

DATA = Data ()

COMPANY_WORD_RE = re.compile(r"[A-Za-z0-9]+")
COMPANY_SUFFIXES_BY_TOKENS = {
	("inc",): "Inc.",
	("incorporated",): "Incorporated",
	("corporation",): "Corporation",
	("corp",): "Corp.",
	("company",): "Company",
	("co",): "Co.",
	("group",): "Group",
	("holding",): "Holding",
	("holdings",): "Holdings",
	("llc",): "LLC",
	("ltd",): "Ltd.",
	("limited",): "Limited",
	("plc",): "PLC",
	("lp",): "L.P.",
	("partners",): "Partners",
}
COMPANY_SUFFIX_TOKENS = {token for suffix_tokens in COMPANY_SUFFIXES_BY_TOKENS for token in suffix_tokens}
COMPANY_WORDS = None
COMPANY_SUFFIXES = None


def _normalize_company_word(word):
	if not word:
		return None
	if word.isdigit() or len(word) <= 2 and not word.isupper():
		return None
	if word.lower() in COMPANY_SUFFIX_TOKENS:
		return None
	if word.lower() in {"and", "the", "of"}:
		return None
	if word.isupper():
		return word
	return word[0].upper() + word[1:].lower()


def _load_company_terms():
	words = {}
	suffixes = {}
	for company_name in DATA.companies:
		tokens = COMPANY_WORD_RE.findall(company_name)
		if not tokens:
			continue
		suffix = None
		for suffix_tokens in sorted(COMPANY_SUFFIXES_BY_TOKENS, key=len, reverse=True):
			length = len(suffix_tokens)
			if len(tokens) < length:
				continue
			if tuple(token.lower() for token in tokens[-length:]) == suffix_tokens:
				suffix = COMPANY_SUFFIXES_BY_TOKENS[suffix_tokens]
				tokens = tokens[:-length]
				break
		if suffix:
			suffixes[suffix] = None
		if len(tokens) == 1:
			continue
		for token in tokens:
			normalized = _normalize_company_word(token)
			if normalized:
				words[normalized] = None
	return tuple(words), tuple(suffixes)


def _company_terms():
	global COMPANY_WORDS, COMPANY_SUFFIXES
	if COMPANY_WORDS is None or COMPANY_SUFFIXES is None:
		COMPANY_WORDS, COMPANY_SUFFIXES = _load_company_terms()
	return COMPANY_WORDS, COMPANY_SUFFIXES


def _company_name():
	words, suffixes = _company_terms()
	first = random.choice(words)
	parts = [first]
	if len(words) > 1:
		second = random.choice(words)
		for _ in range(5):
			if second != first:
				break
			second = random.choice(words)
		if second != first:
			parts.append(second)
	if suffixes:
		parts.append(random.choice(suffixes))
	return " ".join(parts)

# -----------------------------------------------------------------------------
#
# HIGH-LEVEL API
#
# -----------------------------------------------------------------------------

def email():
	return random.choice(DATA.users) + "@" + random.choice(DATA.domains)

def emails(count=10):
	return [email() for _ in range(count)]

def company():
	return _company_name()

def user():
	return random.choice(DATA.users)

def name(male=False,female=False):
	if female:
		return random.choice(DATA.femaleFirstNames) + " " + random.choice(DATA.lastNames)
	elif male:
		return random.choice(DATA.maleFirstNames) + " " + random.choice(DATA.lastNames)
	else:
		return random.choice(random.choice((DATA.maleFirstNames,DATA.femaleFirstNames))) + " " + random.choice(DATA.lastNames)

def firstName(male=False, female=False):
	if female:
		return random.choice(DATA.femaleFirstNames)
	elif male:
		return random.choice(DATA.maleFirstNames)
	else:
		return random.choice(random.choice((DATA.maleFirstNames,DATA.femaleFirstNames)))

def lastName(male=False,female=False):
	if female:
		return random.choice(DATA.lastNames)
	elif male:
		return random.choice(DATA.lastNames)
	else:
		return random.choice(DATA.lastNames)

def phone():
	n = [number(1, 99)] + [number(0, 10) for _ in range(0,11)]
	return "+{0} ({1}{2}{3})-{4}{5}{6}{7}-{8}{9}{10}{11}".format(*n)

def zip():
	return number (10, 99) * 1000 + number (1,9) * 100 + number (0,100)

def address():
	return "{0}, {1}".format(
		number (1, 10000),
		random.choice(DATA.streets)
	)

def city():
	return random.choice(DATA.cities)

def country():
	return random.choice(DATA.countries)

# -----------------------------------------------------------------------------
#
# DATES
#
# -----------------------------------------------------------------------------

def day():
	return random.choice((
		"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
	))

def month():
	return random.choice((
		"January", "February", "March", "April", "May", "June", "July",
		"August", "September", "October", "November", "December",
	))

def seconds():
	return random.randint(0,59)

def hour():
	return "{0:02d}:{1:02d}".format(random.randint(1,24), random.randint(0,59))

def now():
	return datetime.datetime.now()

def number( start=1, end=100):
	return random.randint(start, end)

def date(seconds=0, minutes=0, hours=0, days=0, weeks=0, months=0, years=0, before=None, after=None):
	"""Returns a new date within the last days, weeks, months and years"""
	time_range =  seconds + minutes * 60 + hours * 60 * 60
	time_range += days         * 24 * 60 * 60
	time_range += weeks  *  7  * 24 * 60 * 60
	time_range += months * 30  * 24 * 60 * 60
	time_range += years  * 365 * 24 * 60 * 60
	before = before or now ()
	if after:
		# We make sure that the time range does not exceed the delta between before and after
		time_range = min(int((before - after).total_seconds()), time_range)
	if time_range:
		return before - datetime.timedelta(seconds=random.randrange(0, time_range))
	else:
		return now ()

def time(seconds=0, minutes=0, hours=0, days=0, weeks=0, months=0, years=0):
	"""Returns a new date within the last hours, minutes and seconds."""
	d = date(seconds=seconds, minutes=minutes, hours=hours, days=days, weeks=weeks, months=months, years=years)
	return (d.hour, d.minute, d.second)

# -----------------------------------------------------------------------------
#
# TEXT
#
# -----------------------------------------------------------------------------

def word( lang="en" ):
	return random.choice(DATA.words[lang])

def words( count=1, lang="en" ):
	return [random.choice(DATA.words[lang]) for _ in range(count)]

def text( lang="en", length="regular", wordsPerLine=(2,12) ):
	# FIXME: Should improve by using a Markov-style algorithm
	res = []
	if length == "one":
		length = 1
	elif length == "title":
		length, wordsPerLine = 1, (1, 25)
	elif length == "short":
		length = (2, 8)
	elif length == "regular":
		length = (3, 20)
	elif length == "long":
		length = (6, 40)
	if isinstance(length, (int, float)):
		length = (length, length + 1)
	if isinstance(wordsPerLine, (int, float)):
		wordsPerLine = (wordsPerLine, wordsPerLine + 1)
	words = DATA.words[lang]
	for _ in range(random.randrange(*length)):
		line = []
		for _ in range(random.randrange(*wordsPerLine)):
			word = random.choice(words)
			if not line:
				word = word.capitalize()
			line.append(word)
		res.append(" ".join(line) + ".")
	return " ".join(res)

def topic( lang="en" ):
	return choice(DATA.topics)

def title( lang="en" ):
	return text(lang, "title")

def paragraph( lang="en" ):
	# FIXME: Should do some actual stats here to determine the best range of
	# lines per paragraph
	return text(lang, (5,25))

# -----------------------------------------------------------------------------
#
# GENERIC
#
# -----------------------------------------------------------------------------

def combination( elements, mininum=0 ):
	count = random.randrange(mininum, len(elements))
	res = set()
	while len(res) < count:
		res.add(random.choice(elements))
	return list(res)

def subset( elements, count=1 ):
	return [random.choice(elements) for _ in range(count)]

def choice( elements, length=None ):
	if length is None:
		elements = list(elements)
	length = length or len(elements)
	i = random.randrange(length)
	if type(elements) in (list,tuple):
		return elements[i]
	else:
		j = 0
		for item in elements:
			if j == i:
				return item
			j += 1

def pick( *elements ):
	return choice(elements)

def seed( value ):
	global CURRENT_SEED
	CURRENT_SEED = value
	random.seed(value)
