// src/js/fake/match.js
// Tokenization, normalization, and recognizer registry (exact port from Python match.py)

export const EMAIL_RE = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/;
export const PHONE_RE = /^\+?[\d().\-\s]{7,}$/;
export const WORDS_RE = /[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?/g;
export const DATE_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
export const DATETIME_RE = /^(\d{4})-(\d{2})-(\d{2})([T ])(\d{2}):(\d{2})(?::(\d{2})(\.\d{1,6})?)?(Z|[+-]\d{2}:?\d{2})?$/;

export const WORD_ALIASES = {
	acc: ["acc"],
	addr: ["address"],
	advisor: ["adviser"],
	amount: ["price", "cost", "expense", "salary", "total", "balance", "fee", "tax"],
	bcc: ["email"],
	billing: ["payment", "amount"],
	city: ["town"],
	companies: ["company"],
	company: ["organisation"],
	count: ["quantity", "qty", "volume"],
	country: ["nation"],
	dob: ["date", "birth"],
	expense: ["amount"],
	firstname: ["first", "name"],
	lastname: ["last", "name", "surname"],
	mobilephone: ["mobile", "phone"],
	organisations: ["organisation"],
	organizations: ["organisation"],
	percent: ["percentage", "ratio"],
	phone: ["phone", "mobile"],
	postcode: ["post", "code"],
	postaladdress: ["postal", "address"],
	price: ["amount"],
	qty: ["quantity", "count"],
	salary: ["amount", "income"],
	town: ["city"],
	url: ["link"],
	username: ["user", "name"],
	zip: ["post", "code"],
	password: ["passwd", "pwd"],
	secret: ["secrets", "credential", "key"],
	token: ["authtoken", "auth_token", "accesstoken", "access_token", "refreshtoken"],
	apikey: ["api_key", "apiKey", "client_secret"],
};

export const TYPE_ALIASES = {
	gender: ["gender", "sex", "pronoun", "title"],
	identifier: ["id", "identifier", "number", "code", "ref", "reference", "uuid", "fsp"],
	amount: ["amount", "price", "cost", "expense", "salary", "subtotal", "total", "balance", "income", "revenue", "fee", "tax", "payment", "charge", "premium", "wage", "budget", "profit", "credit", "debit"],
	count: ["count", "quantity", "qty", "items", "units", "volume", "copies"],
	percentage: ["percentage", "percent", "ratio", "rate", "share", "margin"],
	age: ["age", "aged"],
	year: ["year", "yr", "fiscal", "calendar"],
	email: ["email", "mail", "bcc", "cc"],
	phone: ["phone", "mobile", "telephone", "tel", "fax", "cell"],
	name: ["name", "customer", "client", "person", "contact", "employee", "owner", "member"],
	first_name: ["firstname", "first", "given", "forename"],
	last_name: ["lastname", "last", "surname", "family"],
	address: ["address", "street", "road", "line", "billing", "shipping", "postal"],
	city: ["city", "town", "suburb"],
	country: ["country", "nation", "state"],
	company: ["company", "organisation", "organization", "business", "employer"],
	user: ["user", "username", "login", "account", "handle"],
	date: ["date", "dob", "birthday", "birth", "issued", "expiry", "expires", "start", "end"],
	datetime: ["datetime", "timestamp", "created", "updated", "modified", "at", "time"],
	url: ["url", "uri", "link", "website", "site", "domain"],
	symbol: ["symbol", "fqcn", "classname", "class", "type"],
	secret: ["password", "secret", "token", "apikey", "credential", "auth", "key"],
};

export const RECOGNIZERS = {};

export function registerMatch(kind, priority = 0) {
	return (fn) => {
		RECOGNIZERS[kind] = { fn, priority, aliases: TYPE_ALIASES[kind] || [kind] };
		return fn;
	};
}

export function wordParts(text) {
	const tokens = [];
	for (const segment of String(text).split(/[^A-Za-z\d]+/)) {
		if (!segment || /^\*+$/.test(segment)) continue;
		const parts = segment.match(/[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+\d*|[A-Z]+\d*|\d+/g) || [];
		for (const part of parts) {
			const n = part.toLowerCase().trim();
			if (n) tokens.push(n);
		}
	}
	return tokens;
}

export function singularize(wordValue) {
	const word = String(wordValue).trim().toLowerCase();
	if (word.endsWith("ies") && word.length > 3) return `${word.slice(0, -3)}y`;
	if (word.endsWith("ses") && word.length > 3) return word.slice(0, -2);
	if (word.endsWith("s") && !word.endsWith("ss") && word.length > 3) return word.slice(0, -1);
	return word;
}

export function normalizeWord(wordValue) {
	const n = singularize(wordValue);
	if (!n) return n;
	if (n === "organization") return "organisation";
	if (n === "advisor") return "adviser";
	return n;
}

export function semanticTokens(text) {
	const seen = new Set();
	for (const token of wordParts(text)) {
		const normalized = normalizeWord(token);
		if (!normalized) continue;
		seen.add(normalized);
		for (const alias of WORD_ALIASES[normalized] || []) {
			const na = normalizeWord(alias);
			if (na) seen.add(na);
		}
	}
	return Array.from(seen);
}

export function overlapScore(left, right) {
	const lt = Array.isArray(left) ? left.map(normalizeWord).filter(Boolean) : semanticTokens(left);
	const rt = Array.isArray(right) ? right.map(normalizeWord).filter(Boolean) : semanticTokens(right);
	if (!lt.length || !rt.length) return 0;
	const shared = lt.filter(t => rt.includes(t)).length;
	return (2 * shared) / (lt.length + rt.length);
}

// Recognizers
export const recognizeEmail = registerMatch("email", 100)((value) => {
	if (typeof value === "string" && EMAIL_RE.test(value)) return { type: "email", confidence: 1 };
	return null;
});

export const recognizeUrl = registerMatch("url", 90)((value) => {
	if (typeof value !== "string") return null;
	try {
		const u = new URL(value);
		if (u.protocol === "http:" || u.protocol === "https:") return { type: "url", confidence: 1 };
	} catch (_e) {}
	return null;
});

export const recognizePhone = registerMatch("phone", 80)((value) => {
	if (typeof value !== "string" || !PHONE_RE.test(value)) return null;
	if (DATE_RE.test(value) || DATETIME_RE.test(value)) return null;
	const digits = value.replace(/\D/g, "");
	if (digits.length >= 7 && digits.length <= 15) return { type: "phone", confidence: 1 };
	return null;
});

export const recognizeSymbol = registerMatch("symbol", 95)((value) => {
	if (typeof value !== "string") return null;
	if (value.startsWith("eyJ")) return null;
	if (value.startsWith("sk_live_") || value.startsWith("sk_test_") || value.startsWith("ghp_") || value.startsWith("gho_") || value.startsWith("ghs_") || value.startsWith("AKIA")) return null;
	if (value.includes(".") && /[A-Z]/.test(value)) {
		const parts = wordParts(value);
		if (parts.filter(p => p.length > 1).length >= 3) {
			return { type: "symbol", confidence: 1 };
		}
	}
	return null;
});

export const SECRET_RE = /^(?:(?:sk_live_|sk_test_|gh[ops]_)[0-9a-zA-Z]{20,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-+/=]{10,}|[A-Za-z0-9+/]{25,}={0,2})$/;

export const recognizeSecret = registerMatch("secret", 85)((value, _path, context) => {
	if (typeof value !== "string" || !value) return null;
	if (SECRET_RE.test(value)) return { type: "secret", confidence: 1 };
	if (context && Array.isArray(context)) {
		const ctx = context.map(t => normalizeWord(t)).filter(Boolean);
		const secretWords = ["password", "passwd", "pwd", "secret", "token", "apikey", "api_key", "credential", "auth", "key", "dbpassword"];
		if (ctx.some(t => secretWords.includes(t))) {
			return { type: "secret", confidence: 0.9 };
		}
	}
	return null;
});

export default {
	RECOGNIZERS,
	registerMatch,
	wordParts,
	normalizeWord,
	semanticTokens,
	overlapScore,
	recognizeEmail,
	recognizeUrl,
	recognizePhone,
	recognizeSymbol,
	recognizeSecret,
};
