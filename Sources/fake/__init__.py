# encoding: utf-8
# -----------------------------------------------------------------------------
# Project   : Fake
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : Revised BSD License                              © FFunction, inc
# -----------------------------------------------------------------------------
# Creation  : 31-Jul-2012
# Last mod  : 02-Aug-2012
# -----------------------------------------------------------------------------

import os, json, glob, re, random, datetime

__doc__ = """
Allows to easily generate fake text and data.
"""

ROOT  = os.path.dirname(__file__)
DATA  = ROOT + "/data"
TEXTS = {}

# FIXME: Right now the database of names is not localized, but it should be
with file(DATA + "/emails.json")       as f: EMAIL_USERS   = json.load(f)
with file(DATA + "/domains.json")      as f: EMAIL_DOMAINS = json.load(f)
with file(DATA + "/names.json")        as f: NAMES         = json.load(f)
with file(DATA + "/names-male.json")   as f: NAME_MALE     = json.load(f)
with file(DATA + "/names-female.json") as f: NAME_FEMALE   = json.load(f)
with file(DATA + "/words.json")        as f: WORDS         = json.load(f)

def email():
	return random.choice(EMAIL_USERS) + "@" + random.choice(EMAIL_DOMAINS)

def emails(count=10):
	return [email() for _ in range(count)]

def name(male=False,female=False):
	if female:
		return random.choice(NAME_FEMALE) + " " + random.choice(NAMES)
	elif male:
		return random.choice(NAME_FEMALE) + " " + random.choice(NAMES)
	else:
		return random.choice(random.choice((NAME_MALE,NAME_FEMALE))) + " " + random.choice(NAMES)

def now():
	return datetime.datetime.now()

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

def word( lang="en" ):
	return random.choice(WORDS[lang])

def words( count=1, lang="en" ):
	return [random.choice(WORDS[lang]) for _ in range(count)]

def text( lang="en", length="regular", wordsPerLine=(2,12) ):
	# FIXME: Should improve by using a Markov-style algorithm
	res = []
	if   length == "one":     length  = 1
	elif length == "title":   length, wordsPerLine  = 1, (1,25)
	elif length == "short":   length  = (2,8)
	elif length == "regular": length  = (3,20)
	elif length == "long":    length  = (6,40)
	if type(length)       in (int,float,long): length       = (length,length + 1)
	if type(wordsPerLine) in (int,float,long): wordsPerLine = (wordsPerLine,wordsPerLine + 1)
	words = WORDS[lang]
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
		print "Processed", f
	for k in words: words[k] = list(words[k])
	with file(DATA + "/words.json", "w") as f:
		json.dump(words, f)

# EOF
