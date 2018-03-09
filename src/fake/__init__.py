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

import os, json, glob, re, random, datetime

__doc__ = """
Allows to easily generate fake text and data.
"""

VERSION    = "0.9.1"
ROOT_PATH  = os.path.dirname(__file__)
DATA_PATH  = ROOT_PATH + "/data"

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
	return random.choice(DATA.companies)

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
	if   length == "one":     length  = 1
	elif length == "title":   length, wordsPerLine  = 1, (1,25)
	elif length == "short":   length  = (2,8)
	elif length == "regular": length  = (3,20)
	elif length == "long":    length  = (6,40)
	if type(length)       in (int,float): length       = (length,length + 1)
	if type(wordsPerLine) in (int,float): wordsPerLine = (wordsPerLine,wordsPerLine + 1)
	words = DATA.words[lang]
	for l in range(random.randrange(*length)):
		line = []
		for w in range(random.randrange(*wordsPerLine)):
			word = random.choice(words)
			if not line: word = word.capitalize()
			line.append(word)
		res.append(" ".join(line) + ".")
	return " ".join(res)

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
	l   = random.randrange(mininum, len(elements))
	res = set()
	while len(res) < l:
		res.add(random.choice(elements))
	return list(res)

def choice( elements, length=None ):
	if length is None: elements = list(elements)
	length = length or len(elements)
	i = random.randrange(length)
	if type(elements) in (list,tuple):
		return elements[i]
	else:
		j = 0
		for _ in elements:
			if j == i:
				return _
			j += 1

def seed( value ):
	random.seed(value)

# -----------------------------------------------------------------------------
#
# MAIN
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":
	"""Import Lipsum's XML data -- see http://lipsum.sourceforge.net/whatis.php"""
	import xml.dom.minidom
	words = {}
	for f in glob.glob(ROOT + "/text/*.xml"):
		rawxml    = xml.dom.minidom.parse(f)
		textdata  = rawxml.getElementsByTagName('text')[0].firstChild.data
		title     = rawxml.getElementsByTagName('title')[0].firstChild.data
		author    = rawxml.getElementsByTagName('author')[0].firstChild.data
		copyright = rawxml.getElementsByTagName('copyright')[0].firstChild.data
		name      = os.path.splitext(os.path.basename(f))[0]
		lang      = name.split("-")[0]
		textdata  = re.sub("[^\w]+"," ", textdata).strip()
		words.setdefault(lang,set())
		words[lang] = words[lang].union(textdata.split())
		print ("Processed", f)
	for k in words: words[k] = list(words[k])
	with open(DATA + "/words.json", "w") as f:
		json.dump(words, f)

# EOF
