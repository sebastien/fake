"""Deterministic anonymization of nested payloads using seeded recognizers and reversible mappings."""

import datetime
import hashlib
import json
import random
import re

from .data import CURRENT_SEED, DEFAULT_ANONYMIZE_SEED, DATA
from .match import RECOGNIZERS, normalizeWord, semanticTokens, DATE_RE, DATETIME_RE

MAPPING_VERSION = 3

PERSON_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z'\-]+(?: [A-Za-z][A-Za-z'\-]+){0,3}$")

_anonymizerData = getattr(DATA, "anonymizer", {}) or {}

PERSON_NAME_CONTEXT_TOKENS = set(_anonymizerData.get("personNameContextTokens", []))
NON_PERSON_NAME_CONTEXT_TOKENS = {normalizeWord(t) for t in _anonymizerData.get("nonPersonNameContextTokens", [])}
STRUCTURAL_CONTEXT_TOKENS = set(_anonymizerData.get("structuralContextTokens", []))

# Pools sourced from data (full if available for cardinality, else small from anonymizer.json)
FIRST_NAMES = list(getattr(DATA, "maleFirstNames", [])) + list(getattr(DATA, "femaleFirstNames", []))
if not FIRST_NAMES:
	FIRST_NAMES = list(_anonymizerData.get("firstNames", []))
LAST_NAMES = list(getattr(DATA, "lastNames", []))
if not LAST_NAMES:
	LAST_NAMES = list(_anonymizerData.get("lastNames", []))
EMAIL_USERS = _anonymizerData.get("emailUsers", ["patsy", "tami", "vicky", "aldo", "layla", "jack", "aaron", "abigail", "adam", "adrian", "aiden", "alex", "alice", "alyssa", "andrew", "anna", "anthony", "aria", "asher", "ava", "ben", "brook", "caleb", "camila", "carter", "charlotte", "chloe", "chris", "daniel", "david", "dylan", "eleanor", "elijah", "liz", "ella", "emily", "emma", "ethan", "evelyn", "gabe"])
EMAIL_DOMAINS = _anonymizerData.get("emailDomains", ["example.test", "mail.test", "demo.test", "testmail.com"])
STREET_NAMES = list(getattr(DATA, "streets", []))
if not STREET_NAMES:
	STREET_NAMES = list(_anonymizerData.get("streetNames", ["Main Street", "Oak Avenue", "Pine Road", "Maple Lane", "Cedar Drive", "Willow Way", "River Road", "High Street"]))
CITIES = list(getattr(DATA, "cities", []))
if not CITIES:
	CITIES = list(_anonymizerData.get("cities", ["Auckland", "Wellington", "Christchurch", "Queenstown", "Hamilton", "Dunedin"]))

TRANSFORMERS = {}


def transformer(kind):
	"""Register a value transformer for `kind` (used via @transformer decorator)."""

	def decorator(fn):
		TRANSFORMERS[kind] = fn
		return fn

	return decorator


# -----------------------------------------------------------------------------
#
# DERIVER
#
# -----------------------------------------------------------------------------


class Deriver:
	"""Derives deterministic values from a seed and input parts (used internally by Anonymizer)."""

	def __init__(self, seed):
		self.seed = str(seed) if seed is not None else ""

	def digest(self, *parts):
		payload = json.dumps(
			[self.seed] + [self.coerce(part) for part in parts],
			sort_keys=True,
			separators=(",", ":"),
		).encode("utf-8")
		return hashlib.sha256(payload).digest()

	def coerce(self, value):
		if value is None:
			return None
		if isinstance(value, (list, tuple)):
			return [self.coerce(part) for part in value]
		if isinstance(value, dict):
			return {str(k): self.coerce(v) for k, v in sorted(value.items())}
		if isinstance(value, datetime.datetime):
			return value.isoformat()
		if isinstance(value, datetime.date):
			return value.isoformat()
		return str(value)

	def randbelow(self, limit, *parts):
		if limit <= 0:
			return 0
		return int.from_bytes(self.digest(*parts)[:8], "big") % limit

	def signed(self, limit, *parts):
		if limit <= 0:
			return 0
		return self.randbelow(limit * 2 + 1, *parts) - limit

	def choose(self, values, *parts):
		if not values:
			return ""
		return values[self.randbelow(len(values), *parts)]

	def permutation(self, alphabet, *parts):
		items = list(alphabet)
		for i in range(len(items) - 1, 0, -1):
			swap = self.randbelow(i + 1, *parts, i)
			items[i], items[swap] = items[swap], items[i]
		return items


# -----------------------------------------------------------------------------
#
# ANONYMIZER
#
# -----------------------------------------------------------------------------


class Anonymizer:
	def __init__(self, seed=None, variance=0.25, hints=None, whitelist=None, blacklist=None, mapping=None, redact_secrets=False):
		self.seed = (
			CURRENT_SEED
			if seed is None and CURRENT_SEED is not None
			else (seed if seed is not None else DEFAULT_ANONYMIZE_SEED)
		)
		self.variance = variance
		self.redact_secrets = redact_secrets
		self.hints = {normalizeWord(k): v for k, v in (hints or {}).items()}
		self.whitelist = {normalizeWord(k): v for k, v in (whitelist or {}).items()}
		self.blacklist = {normalizeWord(b) for b in (blacklist or [])}
		self.deriver = Deriver(self.seed)
		self.mapping = self.normalizeMapping(mapping, variance, self.seed, redactSecrets=redact_secrets)
		self.reverse_values = {}
		self.forward_values = {}
		if mapping and isinstance(mapping.get("values"), dict):
			for kind, entries in mapping["values"].items():
				if isinstance(entries, dict):
					self.reverse_values[kind] = dict(entries)
					self.forward_values[kind] = {
						mapped: original for original, mapped in entries.items()
					}
		self.direct = {}

	def normalizeMapping(self, mapping, variance, seed, redactSecrets=False):
		values = {}
		if mapping and isinstance(mapping.get("values"), dict):
			for kind, entries in mapping["values"].items():
				if isinstance(entries, dict):
					values[kind] = dict(entries)
		m = {
			"version": MAPPING_VERSION,
			"seed_fingerprint": hashlib.sha256(str(seed).encode()).hexdigest()[:16],
			"rules": {"variance": variance},
			"values": values,
		}
		if redactSecrets or (mapping and mapping.get("secrets")):
			m["secrets"] = True
		return m

	def infer(self, path, context, value):
		if value is None or isinstance(value, bool):
			return None
		for kind, reg in sorted(
			RECOGNIZERS.items(), key=lambda item: -item[1]["priority"]
		):
			if kind == "secret" and not self.redact_secrets:
				continue
			result = reg["fn"](value, path, context, self.hints)
			if result:
				return result
		if isinstance(value, (int, float)):
			return None
		context_tokens = self.contextTokens(context)
		tset = set(context_tokens)
		field_key = path[-1] if path else ""
		full_norm = normalizeWord(str(field_key)) if field_key else ""
		# whitelist (highest precedence explicit)
		if full_norm in self.whitelist:
			return {"type": self.whitelist[full_norm], "confidence": 1.0}
		for token in context_tokens:
			if token in self.whitelist:
				return {"type": self.whitelist[token], "confidence": 1.0}
		# blacklist (explicit preserve)
		if full_norm in self.blacklist:
			return None
		if any(t in self.blacklist for t in tset):
			return None
		# hints override (configurable) -- also support full normalized key
		if full_norm in self.hints and self.hints[full_norm]:
			return {"type": self.hints[full_norm], "confidence": 1.0}
		for token in context_tokens:
			if token in self.hints:
				hkind = self.hints[token]
				if hkind:
					return {"type": hkind, "confidence": 1.0}
		# email key context (even if value not regex matched)
		if any(t in tset for t in ("email", "mail", "bcc", "cc")) and isinstance(value, str):
			return {"type": "email", "confidence": 0.7}
		# last_name context (robust to "last" alone)
		if "lastname" in tset or "surname" in tset or "familyname" in tset or ("last" in tset and "name" in tset):
			return {"type": "last_name", "confidence": 0.85}
		# first_name context (robust)
		if "firstname" in tset or "forename" in tset or "given" in tset or ("first" in tset and "name" in tset):
			return {"type": "first_name", "confidence": 0.8}
		# middle name
		if "middle" in tset or "middlename" in tset:
			return {"type": "first_name", "confidence": 0.6}
		# address context
		if (tset & {"address", "street", "addr", "postaladdress"} or ("line" in tset and "address" in tset)) and isinstance(value, str):
			return {"type": "address", "confidence": 0.75}
		# city / suburb / town / region
		if tset & {"city", "town", "suburb", "region"} and isinstance(value, str):
			return {"type": "city", "confidence": 0.7}
		# all dates (key indicates date + value matches date pattern)
		if tset & {"date", "dob", "birthday", "birth", "birthdate", "dateofbirth"} or (tset & {"datetime", "timestamp", "created", "updated", "modified", "at", "time"}):
			vstr = str(value) if value is not None else ""
			if DATE_RE.match(vstr) or DATETIME_RE.match(vstr):
				return {"type": "date", "confidence": 0.8}
		# any field containing "name" (broad, after non-person)
		if "name" in tset and not (tset & NON_PERSON_NAME_CONTEXT_TOKENS) and isinstance(value, str):
			if self.isPersonName(context_tokens, value):
				return {"type": "name", "confidence": 0.8}
			return {"type": "pii_string", "confidence": 0.6}
		if self.isPersonName(context_tokens, value):
			return {"type": "name", "confidence": 0.8}
		return None

	def contextTokens(self, context):
		context_tokens = []
		for token in context:
			if not isinstance(token, str):
				continue
			for part in semanticTokens(token):
				if part not in context_tokens:
					context_tokens.append(part)
		return context_tokens

	def isPersonName(self, context_tokens, value):
 		if not self.looksLikePersonName(value):
 			return False
 		tokens = set(context_tokens) - STRUCTURAL_CONTEXT_TOKENS
 		if tokens & NON_PERSON_NAME_CONTEXT_TOKENS:
 			return False
 		return bool(tokens & PERSON_NAME_CONTEXT_TOKENS)

	def looksLikePersonName(self, value):
		if not isinstance(value, str):
			return False
		text = value.strip()
		if not PERSON_NAME_RE.match(text):
			return False
		if text.isupper() and text.isalpha() and 2 <= len(text) <= 8:
			return False
		parts = text.split()
		if len(parts) < 1:
			return False
		return all(not any(char.isdigit() for char in part) for part in parts)

	def mappedValue(self, kind, value, generator, reverse=False):
		if reverse:
			return self.reverse_values.get(kind, {}).get(value, value)
		forward = self.forward_values.setdefault(kind, {})
		reverse_values = self.reverse_values.setdefault(kind, {})
		if value in forward:
			return forward[value]
		mapped = generator(0)
		salt = 0
		max_tries = 10000
		while mapped == value or (mapped in reverse_values and reverse_values[mapped] != value):
			salt += 1
			if salt > max_tries:
				# fallback to guarantee unique (for very high cardinality PII under small pools)
				fb = f"Anon-{self.deriver.randbelow(0xffffff, kind, value, salt):06x}"
				mapped = fb
				break
			mapped = generator(salt)
		forward[value] = mapped
		reverse_values[mapped] = value
		self.mapping["values"].setdefault(kind, {})[mapped] = value
		return mapped

	def transformValue(self, value, kind, pathKey, reverse=False):
		if kind in TRANSFORMERS:
			return TRANSFORMERS[kind](self, value, kind, pathKey, reverse)
		return value

	def collectDirect(self, payload, reverse=False):
		self.direct = {}
		for path, context, value in self.iterScalars(payload):
			inferred = self.infer(path, context, value)
			if not inferred:
				continue
			pathKey = ".".join(str(part) for part in path)
			transformed = self.transformValue(
				value, inferred.get("type"), pathKey, reverse
			)
			if transformed != value:
				self.direct[pathKey] = transformed
		return self

	def iterScalars(self, value, path=None, context=None):
		path = path or []
		context = context or []
		if isinstance(value, dict):
			for key, item in value.items():
				yield from self.iterScalars(item, path + [key], context + [key])
		elif isinstance(value, list):
			for i, item in enumerate(value):
				yield from self.iterScalars(item, path + [i], context + ["*"])
		else:
			yield path, context, value

	def apply(self, value, reverse=False, path=None):
		path = path or []
		pathKey = ".".join(str(part) for part in path)
		if pathKey in self.direct:
			return self.direct[pathKey]
		if isinstance(value, dict):
			return {
				key: self.apply(item, reverse, path + [key])
				for key, item in value.items()
			}
		if isinstance(value, list):
			return [
				self.apply(item, reverse, path + [i]) for i, item in enumerate(value)
			]
		return value

	def anonymize(self, payload):
		"""Return anonymized `payload` and the mapping used (populates self.mapping)."""
		self.collectDirect(payload, False)
		return {"value": self.apply(payload, False), "mapping": self.mapping}

	def deanonymize(self, payload):
		self.collectDirect(payload, True)
		return self.apply(payload, True)


@transformer("secret")
def transformSecret(self, value, kind, pathKey, reverse=False):
	if reverse:
		return self.reverse_values.get(kind, {}).get(value, value)
	return self.mappedValue(
		kind,
		value,
		lambda salt: f"[REDACTED-SECRET-{self.deriver.randbelow(16777216, kind, pathKey, value, salt):06x}]",
		reverse,
	)


@transformer("symbol")
def transformSymbol(self, value, kind, path_key, reverse=False):
	return value


@transformer("first_name")
def transformFirstName(self, value, kind, pathKey, reverse=False):
 	return self.mappedValue(
 		kind,
 		value,
 		lambda salt: self.deriver.choose(FIRST_NAMES, kind, pathKey, value, salt),
 		reverse,
 	)


@transformer("name")
def transformName(self, value, kind, pathKey, reverse=False):
	orig = str(value) if value is not None else ""
	orig_words = [w for w in orig.split() if w] if orig else []
	is_single = len(orig_words) <= 1 and " " not in orig
	def makeName(salt):
		if is_single:
			return self.deriver.choose(LAST_NAMES, kind, pathKey, value, salt, "single")
		return "{0} {1}".format(
			self.deriver.choose(FIRST_NAMES, kind, pathKey, value, salt, "first"),
			self.deriver.choose(LAST_NAMES, kind, pathKey, value, salt, "last"),
		)
	def styleMatch(mapped):
		if not orig or not mapped:
			return mapped
		if orig.isupper():
			return mapped.upper()
		if is_single and orig[:1].isupper() and (len(orig) < 2 or orig[1:].islower() or orig[1:].isalpha()):
			return mapped[:1].upper() + mapped[1:].lower() if len(mapped) > 1 else mapped
		if not is_single and " " in mapped:
			return " ".join(w[:1].upper() + w[1:].lower() for w in mapped.split())
		return mapped
	return self.mappedValue(
		kind,
		value,
		lambda salt: styleMatch( makeName(salt) ),
		reverse,
	)


@transformer("email")
def transformEmail(self, value, kind, pathKey, reverse=False):
	pools = getattr(DATA, "anonymizer", {}) or {}
	users = pools.get("emailUsers", [])
	domains = pools.get("emailDomains", [])
	return self.mappedValue(
		kind,
		value,
		lambda salt: "{0}{1}@{2}".format(
			self.deriver.choose(users, kind, pathKey, value, salt),
			self.deriver.randbelow(1000, kind, pathKey, value, salt, "n"),
			self.deriver.choose(domains, kind, pathKey, value, salt, "d"),
		),
		reverse,
	)


@transformer("phone")
def transformPhone(self, value, kind, pathKey, reverse=False):
 	orig = str(value) if value is not None else ""
 	digit_positions = [i for i, c in enumerate(orig) if c.isdigit()]
 	n = len(digit_positions)
 	def generate(salt):
 		if n == 0:
 			return orig
 		new_digits = [
 			str(self.deriver.randbelow(10, kind, pathKey, orig, salt, i))
 			for i in range(n)
 		]
 		out = list(orig)
 		for pos, d in zip(digit_positions, new_digits):
 			out[pos] = d
 		return "".join(out)
 	return self.mappedValue(kind, value, generate, reverse)


@transformer("last_name")
def transformLastName(self, value, kind, pathKey, reverse=False):
	last = list(getattr(DATA, "lastNames", []))
	return self.mappedValue(
		kind,
		value,
		lambda salt: self.deriver.choose(last, kind, pathKey, value, salt),
		reverse,
	)


@transformer("address")
def transformAddress(self, value, kind, pathKey, reverse=False):
	pools = getattr(DATA, "anonymizer", {}) or {}
	streets = pools.get("streetNames", [])
	def generate(salt):
		num = 10 + self.deriver.randbelow(9990, kind, pathKey, value, salt)
		street = self.deriver.choose(streets, kind, pathKey, value, salt)
		return "{0} {1}".format(num, street)
	return self.mappedValue(kind, value, generate, reverse)


@transformer("city")
def transformCity(self, value, kind, pathKey, reverse=False):
	pools = getattr(DATA, "anonymizer", {}) or {}
	cities = pools.get("cities", [])
	return self.mappedValue(
		kind,
		value,
		lambda salt: self.deriver.choose(cities, kind, pathKey, value, salt),
		reverse,
	)


@transformer("date")
def transformDate(self, value, kind, path_key, reverse=False):
	if reverse:
		return self.reverse_values.get(kind, {}).get(value, value)
	def generate(salt):
		vstr = str(value).strip() if value is not None else ""
		try:
			if DATE_RE.match(vstr):
				y, m, d = map(int, DATE_RE.match(vstr).groups())
				dt = datetime.date(y, m, d)
				jitter = max(3, int(21 * (self.variance or 0.25)))
				delta = self.deriver.signed(jitter, kind, path_key, value, salt)
				if delta == 0:
					delta = 1 if (salt % 2 == 0) else -1
				new_dt = dt + datetime.timedelta(days=delta)
				return new_dt.isoformat()
			if DATETIME_RE.match(vstr):
				m = DATETIME_RE.match(vstr)
				y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
				hh = int(m.group(5) or 0)
				mi = int(m.group(6) or 0)
				ss = int(m.group(7) or 0)
				us = 0
				frac = m.group(8)
				if frac:
					us = int((frac[1:] + "000000")[:6])
				tz = m.group(9) or ""
				sep = m.group(4) or "T"
				dt = datetime.datetime(y, mo, d, hh, mi, ss, us)
				jitter = max(3, int(21 * (self.variance or 0.25)))
				day_delta = self.deriver.signed(jitter, kind, path_key, value, salt)
				if day_delta == 0:
					day_delta = 1 if (salt % 2 == 0) else -1
				time_jitter = max(300, int(14400 * (self.variance or 0.25)))
				sec_delta = self.deriver.signed(time_jitter, kind, path_key, value, salt, "time")
				new_dt = dt + datetime.timedelta(days=day_delta, seconds=sec_delta)
				# rebuild similar format
				new_d = new_dt.strftime("%Y-%m-%d")
				new_t = new_dt.strftime("%H:%M:%S")
				if frac:
					fc = len(frac) - 1
					uss = f"{new_dt.microsecond:06d}"[:fc].rstrip("0")
					if uss:
						new_t += "." + uss
				return new_d + sep + new_t + tz
		except Exception:
			pass
		# fallback mapped neutral date
		base = datetime.date(1990, 1, 1)
		jitter = max(3, int(21 * (self.variance or 0.25)))
		delta = self.deriver.signed(jitter, kind, path_key, value, salt)
		return (base + datetime.timedelta(days=abs(delta) % 3650)).isoformat()
	return self.mappedValue(kind, value, generate, reverse)


@transformer("pii_string")
def transformPiiString(self, value, kind, pathKey, reverse=False):
	if reverse:
		return self.reverse_values.get(kind, {}).get(value, value)
	return self.mappedValue(
 		kind,
 		value,
 		lambda salt: "[PII-{0:06x}]".format(self.deriver.randbelow(16777216, kind, pathKey, value, salt)),
 		reverse,
 	)


def guessAnonymizationCategory(field_name, field_value, *, context=None, path=None, hints=None, whitelist=None, blacklist=None):
 	"""Guess the anonymization category/kind for a field (standalone, no side effects)."""
 	a = Anonymizer(seed=0, hints=hints, whitelist=whitelist, blacklist=blacklist)
 	p = path or [field_name]
 	c = context or [field_name]
 	inferred = a.infer(p, c, field_value)
 	return inferred.get("type") if inferred else None


# -----------------------------------------------------------------------------
#
# PUBLIC API
#
# -----------------------------------------------------------------------------
#
# PUBLIC API
#
# -----------------------------------------------------------------------------


def anonymize(payload, seed=None, variance=0.25, hints=None, whitelist=None, blacklist=None, mapping=None, redact_secrets=False):
 	return Anonymizer(
 		seed=seed, variance=variance, hints=hints, whitelist=whitelist, blacklist=blacklist, mapping=mapping, redact_secrets=redact_secrets
 	).anonymize(payload)


def fuzz(payload, seed=None, variance=0.25, hints=None, whitelist=None, blacklist=None, mapping=None, redact_secrets=False):
 	if seed is None:
 		seed = random.randint(0, 2**31 - 1)
 	return anonymize(
 		payload, seed=seed, variance=variance, hints=hints, whitelist=whitelist, blacklist=blacklist, mapping=mapping, redact_secrets=redact_secrets
 	)


def deanonymize(payload, seed=None, variance=0.25, hints=None, whitelist=None, blacklist=None, mapping=None):
 	return Anonymizer(
 		seed=seed, variance=variance, hints=hints, whitelist=whitelist, blacklist=blacklist, mapping=mapping
 	).deanonymize(payload)


def redact(payload, seed=None, variance=0.25, hints=None, whitelist=None, blacklist=None, mapping=None):
 	return anonymize(payload, seed=seed, variance=variance, hints=hints, whitelist=whitelist, blacklist=blacklist, mapping=mapping, redact_secrets=True)


# EOF
