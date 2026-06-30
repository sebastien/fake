# Module: match
# Tokenization, normalization, and recognizer registry for data classification.

"""Tokenization, normalization, and recognizer registry for data classification."""

import re
from urllib.parse import urlsplit

from .data import DATA

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
PHONE_RE = re.compile(r"^\+?[\d().\-\s]{7,}$")
DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DATETIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})([T ])(\d{2}):(\d{2})(?::(\d{2})(\.\d{1,6})?)?(Z|[+-]\d{2}:?\d{2})?$")
WORDS_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")

def getAliases():
	a = getattr(DATA, "aliases", None)
	if a:
		return a.get("wordAliases", {}), a.get("typeAliases", {})
	return {}, {}

RECOGNIZERS = {}


# -----------------------------------------------------------------------------
#
# TOKENS
#
# -----------------------------------------------------------------------------


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
	"""Return deduplicated semantic tokens for `text` (includes aliases from data)."""
	wordAliases, _ = getAliases()
	tokens = []
	for token in wordParts(text):
		normalized = normalizeWord(token)
		if not normalized:
			continue
		tokens.append(normalized)
		for alias in wordAliases.get(normalized, []):
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


# -----------------------------------------------------------------------------
#
# REGISTRY
#
# -----------------------------------------------------------------------------


def registerMatch(kind, priority=0):
	"""Register a recognizer `fn` for `kind` with given `priority` (higher wins)."""
	def decorator(fn):
		_, typeAliases = getAliases()
		RECOGNIZERS[kind] = {"fn": fn, "priority": priority, "aliases": typeAliases.get(kind, [kind])}
		return fn

	return decorator


# -----------------------------------------------------------------------------
#
# CORE MATCHES
#
# -----------------------------------------------------------------------------


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
	if re.search(r"\.\d", value):
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
	if value.startswith("eyJ") or value.startswith(("sk_live_", "sk_test_", "ghp_", "gho_", "ghs_", "AKIA")):
		return None
	if DATE_RE.match(value) or DATETIME_RE.match(value):
		return None
	if value.isupper() and value.isalpha() and 2 <= len(value) <= 8:
		return {"type": "symbol", "confidence": 0.9}
	if "." in value and any(c.isupper() for c in value):
		parts = wordParts(value)
		if len([p for p in parts if len(p) > 1]) >= 3:
			return {"type": "symbol", "confidence": 1.0}
	return None


SECRET_RE = re.compile(
    r"^(?:(?:sk_live_|sk_test_|gh[ops]_)[0-9a-zA-Z]{20,}|AKIA[0-9A-Z]{16}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-+/=]{10,}|"
    r"[A-Za-z0-9+/]{25,}={0,2})$"
)


@registerMatch("secret", priority=85)
def recognizeSecret(value, path=None, context=None, hints=None):
	if not isinstance(value, str) or not value:
		return None
	if SECRET_RE.match(value):
		return {"type": "secret", "confidence": 1.0}
	if context:
		context_tokens = [normalizeWord(t) for t in context if isinstance(t, str)]
		secret_keywords = {"password", "passwd", "pwd", "secret", "token", "apikey", "api_key", "credential", "auth", "key", "dbpassword"}
		if any(t in secret_keywords for t in context_tokens):
			return {"type": "secret", "confidence": 0.9}
	return None


# EOF
