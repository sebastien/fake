// src/js/fake.js
// Thin export surface. The real implementation lives in ./fake/data.js and ./fake/anon.js.

export {
	VERSION,
	configure,
	preload,
	clearCache,
	seed,
	name,
	firstName,
	lastName,
	email,
	emails,
	company,
	user,
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
	title,
	paragraph,
	topic,
	choice,
	pick,
	combination,
	subset,
	password,
	apiKey,
} from "./fake/data.js";

export {
	anonymize,
	fuzz,
	deanonymize,
	redact,
} from "./fake/anon.js";

// Default export for convenience (same shape as before)
import * as _data from "./fake/data.js";
import { anonymize, fuzz, deanonymize, redact } from "./fake/anon.js";

const { default: _, ...dataExports } = _data;
const fake = {
	...dataExports,
	anonymize,
	fuzz,
	deanonymize,
	redact,
};

export default fake;
