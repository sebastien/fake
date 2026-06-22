const VERSION = "0.9.1";

const DATASETS = {
	countries: "countries.json",
	cities: "cities.json",
	users: "users.json",
	domains: "domains.json",
	lastNames: "lastnames.json",
	maleFirstNames: "firstnames-male.json",
	femaleFirstNames: "firstnames-female.json",
	words: "words.json",
	streets: "streets.json",
	companies: "companies.json",
	topics: "topics.json",
};

const DEFAULT_BASE_URLS = [
	"https://cdn.jsdelivr.net/gh/sebastien/fake@main/src/py/fake/data/",
	"https://raw.githubusercontent.com/sebastien/fake/main/src/py/fake/data/",
];

const DAYS = [
	"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
];

const MONTHS = [
	"January", "February", "March", "April", "May", "June", "July",
	"August", "September", "October", "November", "December",
];

const state = {
	baseUrls: [...DEFAULT_BASE_URLS],
	cacheDir: ".cache/fake",
	data: {},
	loaded: false,
	loadPromise: null,
};

class PythonRandom {
	constructor() {
		this.mt = new Uint32Array(624);
		this.index = 624;
		this.seed();
	}

	seed(value = null) {
		if (value === null || value === undefined) {
			this.initGenrand(Date.now() >>> 0);
			return;
		}

		if (typeof value === "bigint") {
			this.initByArray(bigIntToKeyArray(value));
			return;
		}

		if (typeof value === "number" && Number.isFinite(value) && Number.isInteger(value)) {
			this.initByArray(bigIntToKeyArray(BigInt(value)));
			return;
		}

		// Python-compatible parity is best for integer seeds. Other seed types fall
		// back to a deterministic UTF-8 byte expansion.
		this.initByArray(bytesToKeyArray(new TextEncoder().encode(String(value))));
	}

	initGenrand(seed) {
		this.mt[0] = seed >>> 0;
		for (let i = 1; i < 624; i += 1) {
			const previous = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
			this.mt[i] = (((Math.imul(1812433253, previous) >>> 0) + i) >>> 0);
		}
		this.index = 624;
	}

	initByArray(key) {
		const initKey = key.length ? key : [0];
		this.initGenrand(19650218);
		let i = 1;
		let j = 0;
		let k = Math.max(624, initKey.length);
		for (; k > 0; k -= 1) {
			const previous = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
			this.mt[i] = (
				(this.mt[i] ^ Math.imul(previous, 1664525)) + initKey[j] + j
			) >>> 0;
			i += 1;
			j += 1;
			if (i >= 624) {
				this.mt[0] = this.mt[623];
				i = 1;
			}
			if (j >= initKey.length) {
				j = 0;
			}
		}
		for (k = 623; k > 0; k -= 1) {
			const previous = this.mt[i - 1] ^ (this.mt[i - 1] >>> 30);
			this.mt[i] = ((this.mt[i] ^ Math.imul(previous, 1566083941)) - i) >>> 0;
			i += 1;
			if (i >= 624) {
				this.mt[0] = this.mt[623];
				i = 1;
			}
		}
		this.mt[0] = 0x80000000;
		this.index = 624;
	}

	twist() {
		for (let i = 0; i < 624; i += 1) {
			const y = ((this.mt[i] & 0x80000000) + (this.mt[(i + 1) % 624] & 0x7fffffff)) >>> 0;
			let value = this.mt[(i + 397) % 624] ^ (y >>> 1);
			if (y & 1) {
				value ^= 0x9908b0df;
			}
			this.mt[i] = value >>> 0;
		}
		this.index = 0;
	}

	genrandInt32() {
		if (this.index >= 624) {
			this.twist();
		}
		let y = this.mt[this.index];
		this.index += 1;
		y ^= y >>> 11;
		y ^= (y << 7) & 0x9d2c5680;
		y ^= (y << 15) & 0xefc60000;
		y ^= y >>> 18;
		return y >>> 0;
	}

	random() {
		const a = this.genrandInt32() >>> 5;
		const b = this.genrandInt32() >>> 6;
		return (a * 67108864 + b) / 9007199254740992;
	}

	getrandbits(k) {
		if (!Number.isInteger(k) || k < 0) {
			throw new RangeError("number of bits must be a non-negative integer");
		}
		if (k === 0) {
			return 0n;
		}
		let bits = 0n;
		let remaining = k;
		while (remaining >= 32) {
			bits = (bits << 32n) | BigInt(this.genrandInt32());
			remaining -= 32;
		}
		if (remaining > 0) {
			bits = (bits << BigInt(remaining)) | BigInt(this.genrandInt32() >>> (32 - remaining));
		}
		return bits;
	}

	randbelow(n) {
		if (!Number.isInteger(n) || n <= 0) {
			throw new RangeError("n must be a positive integer");
		}
		const bitLength = Math.floor(Math.log2(n)) + 1;
		let result = Number(this.getrandbits(bitLength));
		while (result >= n) {
			result = Number(this.getrandbits(bitLength));
		}
		return result;
	}

	randrange(start, stop = null) {
		if (stop === null) {
			if (!Number.isInteger(start) || start <= 0) {
				throw new RangeError("empty range for randrange()");
			}
			return this.randbelow(start);
		}
		if (!Number.isInteger(start) || !Number.isInteger(stop)) {
			throw new TypeError("randrange() requires integer arguments");
		}
		const width = stop - start;
		if (width <= 0) {
			throw new RangeError("empty range for randrange()");
		}
		return start + this.randbelow(width);
	}

	randint(start, end) {
		if (!Number.isInteger(start) || !Number.isInteger(end)) {
			throw new TypeError("randint() requires integer arguments");
		}
		return this.randrange(start, end + 1);
	}
	}

const rng = new PythonRandom();

function bigIntToKeyArray(value) {
	let remaining = value < 0n ? -value : value;
	if (remaining === 0n) {
		return [0];
	}
	const key = [];
	while (remaining > 0n) {
		key.push(Number(remaining & 0xffffffffn));
		remaining >>= 32n;
	}
	return key;
}

function bytesToKeyArray(bytes) {
	if (!bytes.length) {
		return [0];
	}
	const key = [];
	for (let i = 0; i < bytes.length; i += 4) {
		let value = 0;
		for (let j = 0; j < 4 && i + j < bytes.length; j += 1) {
			value |= bytes[i + j] << (j * 8);
		}
		key.push(value >>> 0);
	}
	return key;
}

function assertPreloaded(name) {
	if (!state.loaded) {
		throw new Error(`fake.preload() must be awaited before calling fake.${name}()`);
	}
	return state.data;
}

function joinUrl(baseUrl, fileName) {
	return `${baseUrl.replace(/\/?$/, "/")}${fileName}`;
}

function configure(options = {}) {
	if (Array.isArray(options.baseUrls) && options.baseUrls.length > 0) {
		state.baseUrls = [...options.baseUrls];
	}
	if (typeof options.cacheDir === "string" && options.cacheDir) {
		state.cacheDir = options.cacheDir;
	}
	return fake;
}

async function getFs() {
	if (typeof Bun === "undefined") {
		return null;
	}
	return import("node:fs/promises");
}

async function ensureCacheDir() {
	const fs = await getFs();
	if (!fs) {
		return;
	}
	await fs.mkdir(state.cacheDir, { recursive: true });
	}

async function readCachedDataset(fileName) {
	const fs = await getFs();
	if (!fs) {
		return null;
	}
	try {
		const raw = await fs.readFile(`${state.cacheDir}/${fileName}`, "utf8");
		return JSON.parse(raw);
	} catch {
		return null;
	}
}

async function writeCachedDataset(fileName, data) {
	const fs = await getFs();
	if (!fs) {
		return;
	}
	await ensureCacheDir();
	await fs.writeFile(`${state.cacheDir}/${fileName}`, JSON.stringify(data), "utf8");
	}

async function fetchDataset(fileName) {
	const errors = [];
	for (const baseUrl of state.baseUrls) {
		const url = joinUrl(baseUrl, fileName);
		try {
			const response = await fetch(url);
			if (!response.ok) {
				errors.push(`${url} -> HTTP ${response.status}`);
				continue;
			}
			return await response.json();
		} catch (error) {
			errors.push(`${url} -> ${error.message}`);
		}
	}
	throw new Error(`Unable to load dataset ${fileName}: ${errors.join("; ")}`);
	}

async function loadDataset(name, fileName) {
	if (Object.hasOwn(state.data, name)) {
		return state.data[name];
	}

	const cached = await readCachedDataset(fileName);
	if (cached !== null) {
		state.data[name] = cached;
		return cached;
	}

	const data = await fetchDataset(fileName);
	state.data[name] = data;
	await writeCachedDataset(fileName, data);
	return data;
	}

async function preload(options = {}) {
	configure(options);
	if (state.loaded) {
		return fake;
	}
	if (state.loadPromise) {
		await state.loadPromise;
		return fake;
	}
	state.loadPromise = (async () => {
		const entries = Object.entries(DATASETS);
		for (const [name, fileName] of entries) {
			await loadDataset(name, fileName);
		}
		state.loaded = true;
	})();
	try {
		await state.loadPromise;
		return fake;
	} finally {
		state.loadPromise = null;
	}
	}

async function clearCache() {
	state.data = {};
	state.loaded = false;
	state.loadPromise = null;
	const fs = await getFs();
	if (!fs) {
		return;
	}
	try {
		await fs.rm(state.cacheDir, { recursive: true, force: true });
	} catch {
		// Ignore cache cleanup failures.
	}
	}

function email() {
	const data = assertPreloaded("email");
	return `${choice(data.users)}@${choice(data.domains)}`;
	}

function emails(count = 10) {
	return Array.from({ length: count }, () => email());
	}

function company() {
	return choice(assertPreloaded("company").companies);
	}

function user() {
	return choice(assertPreloaded("user").users);
	}

function name(male = false, female = false) {
	const data = assertPreloaded("name");
	if (female) {
		return `${choice(data.femaleFirstNames)} ${choice(data.lastNames)}`;
	}
	if (male) {
		return `${choice(data.maleFirstNames)} ${choice(data.lastNames)}`;
	}
	return `${choice(choice([data.maleFirstNames, data.femaleFirstNames]))} ${choice(data.lastNames)}`;
	}

function firstName(male = false, female = false) {
	const data = assertPreloaded("firstName");
	if (female) {
		return choice(data.femaleFirstNames);
	}
	if (male) {
		return choice(data.maleFirstNames);
	}
	return choice(choice([data.maleFirstNames, data.femaleFirstNames]));
	}

function lastName(male = false, female = false) {
	void male;
	void female;
	return choice(assertPreloaded("lastName").lastNames);
	}

function phone() {
	const numbers = [number(1, 99), ...Array.from({ length: 11 }, () => number(0, 10))];
	return `+${numbers[0]} (${numbers[1]}${numbers[2]}${numbers[3]})-${numbers[4]}${numbers[5]}${numbers[6]}${numbers[7]}-${numbers[8]}${numbers[9]}${numbers[10]}${numbers[11]}`;
	}

function zip() {
	return number(10, 99) * 1000 + number(1, 9) * 100 + number(0, 100);
	}

function address() {
	return `${number(1, 10000)}, ${choice(assertPreloaded("address").streets)}`;
	}

function city() {
	return choice(assertPreloaded("city").cities);
	}

function country() {
	return choice(assertPreloaded("country").countries);
	}

function day() {
	return choice(DAYS);
	}

function month() {
	return choice(MONTHS);
	}

function seconds() {
	return rng.randint(0, 59);
	}

function hour() {
	return `${String(rng.randint(1, 24)).padStart(2, "0")}:${String(rng.randint(0, 59)).padStart(2, "0")}`;
	}

function now() {
	return new Date();
	}

function number(start = 1, end = 100) {
	return rng.randint(start, end);
	}

function date(secondsValue = 0, minutes = 0, hours = 0, days = 0, weeks = 0, months = 0, years = 0, before = null, after = null) {
	let timeRange = secondsValue + minutes * 60 + hours * 60 * 60;
	timeRange += days * 24 * 60 * 60;
	timeRange += weeks * 7 * 24 * 60 * 60;
	timeRange += months * 30 * 24 * 60 * 60;
	timeRange += years * 365 * 24 * 60 * 60;
	const beforeDate = before || now();
	if (after) {
		timeRange = Math.min(Math.trunc((beforeDate.getTime() - after.getTime()) / 1000), timeRange);
	}
	if (timeRange) {
		return new Date(beforeDate.getTime() - rng.randrange(timeRange) * 1000);
	}
	return now();
	}

function time(secondsValue = 0, minutes = 0, hours = 0, days = 0, weeks = 0, months = 0, years = 0) {
	const result = date(secondsValue, minutes, hours, days, weeks, months, years);
	return [result.getHours(), result.getMinutes(), result.getSeconds()];
	}

function word(lang = "en") {
	return choice(assertPreloaded("word").words[lang]);
	}

function words(count = 1, lang = "en") {
	const values = assertPreloaded("words").words[lang];
	return Array.from({ length: count }, () => choice(values));
	}

function text(lang = "en", length = "regular", wordsPerLine = [2, 12]) {
	let computedLength = length;
	let computedWordsPerLine = wordsPerLine;
	if (computedLength === "one") {
		computedLength = 1;
	} else if (computedLength === "title") {
		computedLength = 1;
		computedWordsPerLine = [1, 25];
	} else if (computedLength === "short") {
		computedLength = [2, 8];
	} else if (computedLength === "regular") {
		computedLength = [3, 20];
	} else if (computedLength === "long") {
		computedLength = [6, 40];
	}
	if (typeof computedLength === "number") {
		computedLength = [computedLength, computedLength + 1];
	}
	if (typeof computedWordsPerLine === "number") {
		computedWordsPerLine = [computedWordsPerLine, computedWordsPerLine + 1];
	}
	const values = assertPreloaded("text").words[lang];
	const result = [];
	const lineCount = rng.randrange(computedLength[0], computedLength[1]);
	for (let lineIndex = 0; lineIndex < lineCount; lineIndex += 1) {
		const line = [];
		const wordsInLine = rng.randrange(computedWordsPerLine[0], computedWordsPerLine[1]);
		for (let wordIndex = 0; wordIndex < wordsInLine; wordIndex += 1) {
			let item = choice(values);
			if (line.length === 0) {
				item = item.charAt(0).toUpperCase() + item.slice(1);
			}
			line.push(item);
		}
		result.push(`${line.join(" ")}.`);
	}
	return result.join(" ");
	}

function topic(lang = "en") {
	void lang;
	return choice(assertPreloaded("topic").topics);
	}

function title(lang = "en") {
	return text(lang, "title");
	}

function paragraph(lang = "en") {
	return text(lang, [5, 25]);
	}

function combination(elements, mininum = 0) {
	const length = rng.randrange(mininum, elements.length);
	const result = new Set();
	while (result.size < length) {
		result.add(choice(elements));
	}
	return [...result];
	}

function subset(elements, count = 1) {
	return Array.from({ length: count }, () => choice(elements));
	}

function choice(elements, length = null) {
	if (length === null) {
		const values = Array.from(elements);
		return values[rng.randrange(values.length)];
	}
	const index = rng.randrange(length);
	if (Array.isArray(elements) || typeof elements === "string") {
		return elements[index];
	}
	let current = 0;
	for (const value of elements) {
		if (current === index) {
			return value;
		}
		current += 1;
	}
	return undefined;
	}

function pick(...elements) {
	return choice(elements);
	}

function seed(value) {
	rng.seed(value);
	return fake;
	}

const fake = {
	VERSION,
	DATASETS,
	configure,
	preload,
	clearCache,
	email,
	emails,
	company,
	user,
	name,
	firstName,
	lastName,
	phone,
	zip,
	address,
	city,
	country,
	day,
	month,
	seconds,
	hour,
	now,
	number,
	date,
	time,
	word,
	words,
	text,
	topic,
	title,
	paragraph,
	combination,
	subset,
	choice,
	pick,
	seed,
};

export {
	VERSION,
	DATASETS,
	configure,
	preload,
	clearCache,
	email,
	emails,
	company,
	user,
	name,
	firstName,
	lastName,
	phone,
	zip,
	address,
	city,
	country,
	day,
	month,
	seconds,
	hour,
	now,
	number,
	date,
	time,
	word,
	words,
	text,
	topic,
	title,
	paragraph,
	combination,
	subset,
	choice,
	pick,
	seed,
};



export default fake;
