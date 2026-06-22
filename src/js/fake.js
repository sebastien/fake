// src/js/fake.js
// Thin export surface. The real implementation lives in ./fake/data.js, ./fake/anon.js and ./fake/match.js.

export * from "./fake/data.js";
export * from "./fake/anon.js";
export * from "./fake/match.js";

// Default export for convenience (same shape as before)
import * as data from "./fake/data.js";
import * as anon from "./fake/anon.js";

const fake = {
	...data,
	...anon,
};

export default fake;
