import json
import pathlib
import re
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "py"))

import fake  # noqa: E402


DATA_DIR = ROOT / "tests" / "data"


def load_fixtures():
	fixtures = []
	for path in sorted(DATA_DIR.glob("*.json")):
		with path.open(encoding="utf-8") as handle:
			fixtures.append((path.name, json.load(handle)))
	return fixtures


def get_path(value, path):
	current = value
	for part in path.split("."):
		if isinstance(current, list):
			current = current[int(part)]
		else:
			current = current[part]
	return current


class AnonymizeFeatureTest(unittest.TestCase):
	maxDiff = None

	def test_fixture_inventory(self):
		fixtures = load_fixtures()
		self.assertEqual(8, len(fixtures))
		for name, fixture in fixtures:
			with self.subTest(name=name):
				self.assertIn("document", fixture)
				self.assertIn("expectations", fixture)
				self.assertIn("symbol_paths", fixture["expectations"])
				self.assertIn("pii_paths", fixture["expectations"])

	def test_symbol_fields_are_preserved(self):
		for name, fixture in load_fixtures():
			original = fixture["document"]
			result = fake.anonymize(original, seed=42)
			anonymized = result["value"]
			for path in fixture["expectations"]["symbol_paths"]:
				with self.subTest(name=name, path=path):
					self.assertEqual(get_path(original, path), get_path(anonymized, path))

	def test_dates_are_fuzzed_but_not_misclassified_as_phones(self):
		fixture = json.loads((DATA_DIR / "insurance-policy.json").read_text(encoding="utf-8"))
		original = fixture["document"]
		result = fake.anonymize(original, seed=42)["value"]
		# all date-keyed date values are now fuzzed within ~3 weeks
		self.assertNotEqual(
			original["policy"]["holder"]["dateOfBirth"],
			result["policy"]["holder"]["dateOfBirth"],
		)
		self.assertNotEqual(
			original["policy"]["claimSummary"]["incidentDate"],
			result["policy"]["claimSummary"]["incidentDate"],
		)
		# still not turned into phones (guard preserved)
		self.assertTrue(result["policy"]["holder"]["dateOfBirth"].startswith("19") or result["policy"]["holder"]["dateOfBirth"].startswith("20"))

	def test_roundtrip_restores_original_document(self):
		for name, fixture in load_fixtures():
			original = fixture["document"]
			result = fake.anonymize(original, seed=42)
			restored = fake.deanonymize(
				result["value"], seed=42, mapping=result["mapping"]
			)
			with self.subTest(name=name):
				self.assertEqual(original, restored)

	def test_mapping_has_expected_shape(self):
		for name, fixture in load_fixtures():
			redact = name == "secrets.json"
			mapping = fake.anonymize(fixture["document"], seed=42, redact_secrets=redact)["mapping"]
			with self.subTest(name=name):
				self.assertEqual(3, mapping["version"])
				self.assertEqual({"variance": 0.25}, mapping["rules"])
				self.assertEqual(16, len(mapping["seed_fingerprint"]))
				self.assertIsInstance(mapping["values"], dict)
				if name == "secrets.json":
					self.assertTrue(mapping.get("secrets", False))

	def test_anonymize_is_deterministic(self):
		for name, fixture in load_fixtures():
			first = fake.anonymize(fixture["document"], seed=42)
			second = fake.anonymize(fixture["document"], seed=42)
			with self.subTest(name=name):
				self.assertEqual(first, second)

	def test_phone_structure_is_preserved(self):
		cases = [
			"232-123-1234",
			"+1 (321)-1231-12311",
			"88-81-12-13",
			"+44 20 7946 0958",
			"+1 (415) 555-0141",
			"1234567",
			"123456789012345",
		]
		for c in cases:
			with self.subTest(value=c):
				res = fake.anonymize({"p": c}, seed=42)["value"]["p"]
				self.assertNotEqual(res, c)
				self.assertEqual(len(re.sub(r"\D", "", res)), len(re.sub(r"\D", "", c)))
				self.assertEqual(re.sub(r"\d", "D", res), re.sub(r"\d", "D", c))
				restored = fake.deanonymize({"p": res}, seed=42, mapping=fake.anonymize({"p": c}, seed=42)["mapping"])["p"]
				self.assertEqual(restored, c)

	def test_pii_fields_are_anonymized(self):
		for name, fixture in load_fixtures():
			original = fixture["document"]
			result = fake.anonymize(original, seed=42, redact_secrets=True)
			anonymized = result["value"]
			for path in fixture["expectations"]["pii_paths"]:
				with self.subTest(name=name, path=path):
					self.assertNotEqual(get_path(original, path), get_path(anonymized, path))

	def test_full_name_fields_are_anonymized_conservatively(self):
		payload = {
			"preferredName": "Isaac Watts",
			"PersonName": "Joanne Watts",
			"adviserName": "Ellen Drenon",
			"fileName": "Isaac Watts.pdf",
			"companyName": "Watts Lending",
			"$type": "com.example.PersonName",
		}
		result = fake.anonymize(payload, seed=42)["value"]
		self.assertNotEqual(payload["preferredName"], result["preferredName"])
		self.assertNotEqual(payload["PersonName"], result["PersonName"])
		self.assertNotEqual(payload["adviserName"], result["adviserName"])
		self.assertEqual(payload["fileName"], result["fileName"])
		self.assertEqual(payload["companyName"], result["companyName"])
		self.assertEqual(payload["$type"], result["$type"])

	def test_hints_and_pii_string_fallback(self):
		payload = {
			"NameOfPerson": "WeirdValue123",
			"lastName": "Smith",
			"someDate": "2020-05-05",
			"emailField": "not-an-email",
		}
		result = fake.anonymize(payload, seed=42, hints={"NameOfPerson": "pii_string", "lastName": "last_name"})["value"]
		self.assertNotEqual(payload["NameOfPerson"], result["NameOfPerson"])
		self.assertTrue(result["NameOfPerson"].startswith("[PII-"))
		self.assertNotEqual(payload["lastName"], result["lastName"])
		# date key without hint still fuzzed if matches date pattern
		self.assertNotEqual(payload["someDate"], result["someDate"])
		# email context forces email transform
		self.assertNotEqual(payload["emailField"], result["emailField"])
		self.assertIn("@", result["emailField"])

		# numeric values under email/address/role/history keys must be preserved as-is (not miscategorized)
		payload2 = {
			"OrganisationGroupAnnualReviewEmailDays": 5,
			"PersonAddressHistory": 0,
			"AdviserPublicCNARole": "User",
			"AdviserDisputeResolutionService": "FDRS",
		}
		result2 = fake.anonymize(payload2, seed=42)["value"]
		self.assertEqual(result2["OrganisationGroupAnnualReviewEmailDays"], 5)
		self.assertEqual(result2["PersonAddressHistory"], 0)
		self.assertEqual(result2["AdviserPublicCNARole"], "User")
		self.assertEqual(result2["AdviserDisputeResolutionService"], "FDRS")


	def test_guess_whitelist_blacklist_and_datetime_time(self):
		# guess func
		self.assertEqual(fake.guessAnonymizationCategory("PersonLastName", "Miller"), "last_name")
		self.assertEqual(fake.guessAnonymizationCategory("PersonTwoFactorAuthStatus", "Disabled"), None)
		# whitelist forces even for status like
		self.assertEqual(fake.guessAnonymizationCategory("FooStatus", "Bar", whitelist={"FooStatus": "symbol"}), "symbol")
		# blacklist preserves
		self.assertIsNone(fake.guessAnonymizationCategory("SecretField", "val", blacklist=["SecretField"]))

		# numeric and role enums should not be miscategorized
		self.assertIsNone(fake.guessAnonymizationCategory("OrganisationGroupAnnualReviewEmailDays", 5))
		self.assertIsNone(fake.guessAnonymizationCategory("PersonAddressHistory", 0))
		self.assertIsNone(fake.guessAnonymizationCategory("AdviserPublicCNARole", "User"))
		# acronym/enum id under service key -> symbol (preserved, not name)
		self.assertEqual(fake.guessAnonymizationCategory("AdviserDisputeResolutionService", "FDRS"), "symbol")
		# datetime with time should jitter both
		p = {"created": "2026-04-08T03:12:25.715309Z"}
		r = fake.anonymize(p, seed=42)["value"]["created"]
		self.assertNotEqual(p["created"], r)
		# date part may differ, time part should often differ
		self.assertTrue(r.startswith("2026-") or r.startswith("2025-") or r.startswith("2027-"))  # within jitter
		# use whitelist to preserve a category
		r2 = fake.anonymize(p, seed=42, whitelist={"created": "symbol"})["value"]["created"]
		self.assertEqual(p["created"], r2)

	def test_python_and_js_outputs_are_interchangeable(self):
		for name, fixture in load_fixtures():
			python_result = fake.anonymize(fixture["document"], seed=42)
			fixture_path = DATA_DIR / name
			script = """
import { anonymize } from './src/js/fake/anon.js';
import { readFileSync } from 'node:fs';
const fixture = JSON.parse(readFileSync(process.argv[process.argv.length - 1], 'utf8'));
const result = await anonymize(fixture.document, 42);
console.log(JSON.stringify(result));
""".strip()
			completed = subprocess.run(
				["bun", "--input-type=module", "-e", script, str(fixture_path)],
				check=True,
				capture_output=True,
				text=True,
				cwd=str(ROOT),
			)
			js_result = json.loads(completed.stdout)
			with self.subTest(name=name):
				self.assertEqual(python_result, js_result)


if __name__ == "__main__":
	unittest.main()
