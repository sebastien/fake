# Module: match
# Tokenization, normalization, semantic matching, and recognizer registry for classification used by anonymization.

"""Tokenization, normalization, and recognizer registry for data classification."""

import re
from urllib.parse import urlsplit

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
PHONE_RE = re.compile(r"^\+?[\d().\-\s]{7,}$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DATETIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})([T ])(\d{2}):(\d{2})(?::(\d{2})(\.\d{1,6})?)?(Z|[+-]\d{2}:?\d{2})?$")
INTEGER_RE = re.compile(r"^[+-]?\d+$")
DECIMAL_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+)$")
WORDS_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")

GENDER_VALUES = {"male", "female", "m", "f", "man", "woman", "boy", "girl", "non-binary", "nonbinary", "unknown", "other", "prefer not to say"}

WORD_ALIASES = {
	"acc": ["acc"],
	"addr": ["address"],
	"advisor": ["adviser"],
	"amount": ["price", "cost", "expense", "salary", "total", "balance", "fee", "tax"],
	"bcc": ["email"],
	"billing": ["payment", "amount"],
	"city": ["town"],
	"companies": ["company"],
	"company": ["organisation"],
	"count": ["quantity", "qty", "volume"],
	"country": ["nation"],
	"dob": ["date", "birth"],
	"expense": ["amount"],
	"firstname": ["first", "name"],
	"lastname": ["last", "name", "surname"],
	"mobilephone": ["mobile", "phone"],
	"organisations": ["organisation"],
	"organizations": ["organisation"],
	"percent": ["percentage", "ratio"],
	"phone": ["phone", "mobile"],
	"postcode": ["post", "code"],
	"postaladdress": ["postal", "address"],
	"price": ["amount"],
	"qty": ["quantity", "count"],
	"salary": ["amount", "income"],
	"town": ["city"],
	"url": ["link"],
	"username": ["user", "name"],
	"zip": ["post", "code"],
}

TYPE_ALIASES = {
	"gender": ["gender", "sex", "pronoun", "title"],
	"identifier": ["id", "identifier", "number", "code", "ref", "reference", "uuid", "fsp"],
	"amount": ["amount", "price", "cost", "expense", "salary", "subtotal", "total", "balance", "income", "revenue", "fee", "tax", "payment", "charge", "premium", "wage", "budget", "profit", "credit", "debit"],
	"count": ["count", "quantity", "qty", "items", "units", "volume", "copies"],
	"percentage": ["percentage", "percent", "ratio", "rate", "share", "margin"],
	"age": ["age", "aged"],
	"year": ["year", "yr", "fiscal", "calendar"],
	"email": ["email", "mail", "bcc", "cc"],
	"phone": ["phone", "mobile", "telephone", "tel", "fax", "cell"],
	"name": ["name", "customer", "client", "person", "contact", "employee", "owner", "member"],
	"first_name": ["firstname", "first", "given", "forename"],
	"last_name": ["lastname", "last", "surname", "family"],
	"address": ["address", "street", "road", "line", "billing", "shipping", "postal"],
	"city": ["city", "town", "suburb"],
	"country": ["country", "nation", "state"],
	"company": ["company", "organisation", "organization", "business", "employer"],
	"user": ["user", "username", "login", "account", "handle"],
	"date": ["date", "dob", "birthday", "birth", "issued", "expiry", "expires", "start", "end"],
	"datetime": ["datetime", "timestamp", "created", "updated", "modified", "at", "time"],
	"url": ["url", "uri", "link", "website", "site", "domain"],
	"symbol": ["symbol", "fqcn", "classname", "class", "type"],
}

RECOGNIZERS = {}


# -----------------------------------------------------------------------------
#
# TOKENS
#
# -----------------------------------------------------------------------------


def words(text):
	"""Return coarse word tokens from `text`."""
	return WORDS_RE.findall(str(text))


def wordParts(text):
	"""Return normalized word parts from `text` (handles camelCase and punctuation)."""
	tokens = []
	for segment in re.split(r"[^A-Za-z\d]+", str(text)):
		if not segment or re.match(r"^\*+$", segment):
			continue
		parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+\d*|[A-Z]+\d*|\d+", segment)
		for part in parts:
			normalized = part.strip().lower()
			if normalized:
				tokens.append(normalized)
	return tokens


def singularize(wordValue):
	"""Return a simple singular form for `wordValue` (removes common English plurals)."""
	word = str(wordValue).strip().lower()
	if word.endswith("ies") and len(word) > 3:
		return word[:-3] + "y"
	if word.endswith("ses") and len(word) > 3:
		return word[:-2]
	if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
		return word[:-1]
	return word



def normalizeWord(wordValue):
	"""Normalize `wordValue` for semantic matching (handles British spelling and plurals)."""
	normalized = singularize(wordValue)
	if not normalized:
		return normalized
	if normalized == "organization":
		return "organisation"
	if normalized == "advisor":
		return "adviser"
	return normalized


def semanticTokens(text):
	"""Return deduplicated semantic tokens for `text` (includes aliases from WORD_ALIASES)."""
	tokens = []
	for token in wordParts(text):
		normalized = normalizeWord(token)
		if not normalized:
			continue
		tokens.append(normalized)
		for alias in WORD_ALIASES.get(normalized, []):
			normalized_alias = normalizeWord(alias)
			if normalized_alias:
				tokens.append(normalized_alias)
	seen = []
	for token in tokens:
		if token not in seen:
			seen.append(token)
	return seen


def overlapScore(left, right):
	"""Return overlap score (0.0-1.0) between `left` and `right` semantic token sets."""
	left_tokens = semanticTokens(left) if not isinstance(left, (list, tuple)) else [normalizeWord(item) for item in left]
	right_tokens = semanticTokens(right) if not isinstance(right, (list, tuple)) else [normalizeWord(item) for item in right]
	if not left_tokens or not right_tokens:
		return 0.0
	shared = len(set(left_tokens) & set(right_tokens))
	return (2.0 * shared) / (len(set(left_tokens)) + len(set(right_tokens)))


def semanticMatch(left, right):
	"""Return overlap metrics dict for `left` and `right`."""
	overlap = overlapScore(left, right)
	return {"overlap": overlap, "score": overlap}


# -----------------------------------------------------------------------------
#
# REGISTRY
#
# -----------------------------------------------------------------------------


def registerMatch(kind, priority=0):
	"""Register a recognizer `fn` for `kind` with given `priority` (higher wins)."""
	def decorator(fn):
		RECOGNIZERS[kind] = {"fn": fn, "priority": priority, "aliases": TYPE_ALIASES.get(kind, [kind])}
		return fn

	return decorator


# -----------------------------------------------------------------------------
#
# CORE MATCHES
#
# -----------------------------------------------------------------------------


normalize_word = normalizeWord
wordparts = wordParts
semantic_tokens = semanticTokens
overlap_score = overlapScore
semantic_match = semanticMatch
recognizer = registerMatch
register_recognizer = registerMatch
register_match = registerMatch


@registerMatch("email", priority=100)
def recognizeEmail(value, path=None, context=None, hints=None):
	"""Recognize email-like strings (uses EMAIL_RE)."""
	if isinstance(value, str) and EMAIL_RE.match(value):
		return {"type": "email", "confidence": 1.0}
	return None


@registerMatch("url", priority=90)
def recognizeUrl(value, path=None, context=None, hints=None):
	"""Recognize HTTP/HTTPS URLs (uses urlsplit)."""
	if not isinstance(value, str):
		return None
	try:
		parsed = urlsplit(value)
		if parsed.scheme in ("http", "https") and parsed.netloc:
			return {"type": "url", "confidence": 1.0}
	except ValueError:
		return None
	return None


@registerMatch("phone", priority=80)
def recognizePhone(value, path=None, context=None, hints=None):
	"""Recognize simple phone numbers (uses PHONE_RE and digit length)."""
	if not isinstance(value, str) or not PHONE_RE.match(value):
		return None
	if DATE_RE.match(value) or DATETIME_RE.match(value):
		return None
	digits = re.sub(r"\D", "", value)
	if 7 <= len(digits) <= 15:
		return {"type": "phone", "confidence": 1.0}
	return None


@registerMatch("symbol", priority=95)
def recognizeSymbol(value, path=None, context=None, hints=None):
	"""Recognize Java-style FQCNs and technical symbols (prevents name replacement on class names)."""
	if not isinstance(value, str):
		return None
	if "." in value and any(c.isupper() for c in value):
		parts = wordParts(value)
		if len([p for p in parts if len(p) > 1]) >= 3:
			return {"type": "symbol", "confidence": 1.0}
	return None


recognize_email = recognizeEmail
recognize_url = recognizeUrl
recognize_phone = recognizePhone
recognize_symbol = recognizeSymbol


# EOF
