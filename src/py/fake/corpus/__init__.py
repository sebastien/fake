"""Markov-chain text generator backed by literary corpora.

Corpus files are public-domain literary works in multiple languages.
Provides markovText() for natural text generation used by fake.text().
"""

import os
import re
import random
from html.parser import HTMLParser

from ..data import DATA

ROOT_PATH = os.path.dirname(__file__)

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:'[A-Za-zÀ-ÿ0-9]+)?")

CORPORA = {}

def getLanguageMap():
	c = getattr(DATA, "corpora", None)
	if c and isinstance(c, dict):
		return c
	return {
		"en": ["en-faust.xml", "en-childharold.xml", "en-decameron.xml", "en-theraven.xml"],
		"de": ["de-inderfremde.xml"],
		"fr": ["fr-lebateauivre.xml", "fr-lemasque.xml"],
		"es": ["es-tierrayluna.xml"],
		"eo": ["eo-robinsonokruso.xml"],
		"hu": ["hu-nagyonfaj.xml", "hu-omagyar.xml"],
		"la": ["la-loremipsum.xml"],
	}


class _TextExtractor(HTMLParser):
	"""Extracts plain text from the <text> element in our corpus XML."""

	def __init__(self):
		super().__init__()
		self.collecting = False
		self.lines = []

	def handle_starttag(self, tag, attrs):
		if tag == "text":
			self.collecting = True

	def handle_endtag(self, tag):
		if tag == "text":
			self.collecting = False

	def handle_data(self, data):
		if self.collecting:
			cleaned = data.strip()
			if cleaned:
				self.lines.append(cleaned)


def readFile(path):
	for encoding in ("utf-8", "iso-8859-1", "latin-1", "iso-8859-2"):
		try:
			with open(path, encoding=encoding) as handle:
				return handle.read()
		except (UnicodeDecodeError, LookupError):
			continue
	return ""


def wordsFromText(text):
	return WORD_RE.findall(text)


def buildBigram(lang):
	if lang in CORPORA:
		return CORPORA[lang]
	languageMap = getLanguageMap()
	filenames = languageMap.get(lang, languageMap.get("la", []))
	bigram = {}
	word_counts = {}
	for filename in filenames:
		path = os.path.join(ROOT_PATH, filename)
		if not os.path.isfile(path):
			continue
		content = readFile(path)
		if not content:
			continue
		extractor = _TextExtractor()
		extractor.feed(content)
		for line in extractor.lines:
			tokens = wordsFromText(line)
			if len(tokens) < 2:
				continue
			for i in range(len(tokens) - 1):
				word = tokens[i].lower()
				next_word = tokens[i + 1].lower()
				bigram.setdefault(word, []).append(next_word)
				word_counts[word] = word_counts.get(word, 0) + 1
	# Build starter words (words that appear at the beginning of lines)
	starters = {}
	for filename in filenames:
		path = os.path.join(ROOT_PATH, filename)
		if not os.path.isfile(path):
			continue
		content = readFile(path)
		if not content:
			continue
		extractor = _TextExtractor()
		extractor.feed(content)
		for line in extractor.lines:
			tokens = wordsFromText(line)
			if not tokens:
				continue
			first = tokens[0].lower()
			starters[first] = starters.get(first, 0) + 1
	model = {"bigram": bigram, "starters": list(starters), "counts": word_counts}
	CORPORA[lang] = model
	return model


def generateSentence(model, minWords=4, maxWords=30):
	"""Generate a sentence using the bigram model."""
	bigram = model["bigram"]
	starters = model["starters"]
	words = []
	current = random.choice(starters)
	words.append(current)
	for _ in range(maxWords - 1):
		next_words = bigram.get(current)
		if not next_words:
			break
		current = random.choice(next_words)
		words.append(current)
		if len(words) >= minWords:
			break
	if not words:
		return ""
	result = " ".join(words)
	result = result[0].upper() + result[1:] + "."
	return result


def markovText(lang="en", length="regular", wordsPerLine=(2, 12)):
	"""Generate text using a Markov chain built from literary corpora.

	Parameters mirror `fake.text()`: `length` can be "title", "short",
	"regular", "long", or an (int, int) tuple. `wordsPerLine` controls
	the number of sentences per generated line (default (2, 12)).
	"""
	model = buildBigram(lang)
	computed = length
	if computed == "one":
		computed = 1
	elif computed == "title":
		computed, wordsPerLine = 1, (1, 25)
	elif computed == "short":
		computed = (2, 8)
	elif computed == "regular":
		computed = (3, 20)
	elif computed == "long":
		computed = (6, 40)
	if isinstance(computed, (int, float)):
		computed = (computed, computed + 1)
	if isinstance(wordsPerLine, (int, float)):
		wordsPerLine = (wordsPerLine, wordsPerLine + 1)
	res = []
	for _ in range(random.randrange(*computed)):
		line = []
		for _ in range(random.randrange(*wordsPerLine)):
			line.append(generateSentence(model))
		res.append(" ".join(line))
	if not res:
		return generateSentence(model)
	return "\n\n".join(res)
