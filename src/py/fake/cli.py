import argparse
import inspect
import json
import random
import re
import sys

import fake


COUNT_RANGE_RE = re.compile(r"^(\d+)-(\d+)$")
BOOLEAN_TRUE = {"1", "true", "yes", "on"}
BOOLEAN_FALSE = {"0", "false", "no", "off"}
SYSTEM_RANDOM = random.SystemRandom()


def _error(message):
	raise ValueError(message)


def _cli_name(name):
	return name.replace("_", "-").replace(" ", "-")


def _param_aliases(name):
	aliases = {name, _cli_name(name)}
	if any(c.isupper() for c in name):
		pieces = []
		for char in name:
			if char.isupper():
				pieces.append("-")
				pieces.append(char.lower())
			else:
				pieces.append(char)
		aliases.add("".join(pieces).lstrip("-"))
	return aliases


def _parse_bool(value):
	text = value.lower()
	if text in BOOLEAN_TRUE:
		return True
	if text in BOOLEAN_FALSE:
		return False
	_error("invalid boolean value: {0}".format(value))


def _parse_int_range(value, label):
	match = COUNT_RANGE_RE.match(value)
	if not match:
		_error("invalid {0}: {1}".format(label, value))
	start, end = int(match.group(1)), int(match.group(2))
	if end < start:
		_error("invalid {0}: {1}".format(label, value))
	return (start, end)


def _parse_count(value):
	if value.isdigit():
		return int(value)
	start, end = _parse_int_range(value, "count")
	return SYSTEM_RANDOM.randint(start, end)


def _coerce_value(name, parameter, value):
	default = parameter.default
	if isinstance(default, bool):
		return _parse_bool(value)
	if isinstance(default, int) and not isinstance(default, bool):
		try:
			return int(value)
		except ValueError as exc:
			raise ValueError("invalid integer for --{0}: {1}".format(_cli_name(name), value)) from exc
	if name in ("length", "wordsPerLine") and COUNT_RANGE_RE.match(value):
		return _parse_int_range(value, name)
	return value


def _resolve_generator(name):
	if not hasattr(fake, name):
		_error("unknown type: {0}".format(name))
	generator = getattr(fake, name)
	if not callable(generator):
		_error("type is not callable: {0}".format(name))
	return generator


def _build_option_map(signature):
	option_map = {}
	boolean_options = set()
	for name, parameter in signature.parameters.items():
		if parameter.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
			continue
		for alias in _param_aliases(name):
			option_map[alias] = name
		if isinstance(parameter.default, bool):
			for alias in _param_aliases(name):
				boolean_options.add(alias)
	return option_map, boolean_options


def _parse_generator_args(tokens, signature):
	option_map, boolean_options = _build_option_map(signature)
	kwargs = {}
	count = 1
	remaining = list(tokens)
	if remaining and not remaining[-1].startswith("-"):
		count = _parse_count(remaining.pop())

	index = 0
	while index < len(remaining):
		token = remaining[index]
		if not token.startswith("--"):
			_error("unexpected argument: {0}".format(token))

		name_value = token[2:]
		if name_value.startswith("no-"):
			alias = name_value[3:]
			if alias not in boolean_options:
				_error("unsupported option: --{0}".format(name_value))
			kwargs[option_map[alias]] = False
			index += 1
			continue

		if "=" in name_value:
			alias, raw_value = name_value.split("=", 1)
		else:
			alias = name_value
			if alias not in option_map:
				_error("unsupported option: --{0}".format(alias))
			parameter = signature.parameters[option_map[alias]]
			if isinstance(parameter.default, bool):
				kwargs[option_map[alias]] = True
				index += 1
				continue
			index += 1
			if index >= len(remaining):
				_error("missing value for --{0}".format(alias))
			raw_value = remaining[index]

		if alias not in option_map:
			_error("unsupported option: --{0}".format(alias))
		name = option_map[alias]
		kwargs[name] = _coerce_value(name, signature.parameters[name], raw_value)
		index += 1

	return kwargs, count


def _iter_text_lines(value):
	if isinstance(value, (list, tuple)):
		for item in value:
			yield from _iter_text_lines(item)
	else:
		yield str(value)


def build_parser():
	parser = argparse.ArgumentParser(prog="fake")
	parser.add_argument("-s", "--seed")
	parser.add_argument("-f", "--format", choices=("text", "json"), default="text")
	parser.add_argument("type")
	parser.add_argument("args", nargs=argparse.REMAINDER)
	return parser


def main(argv=None):
	parser = build_parser()
	args = parser.parse_args(argv)
	try:
		generator = _resolve_generator(args.type)
		if args.seed is not None:
			fake.seed(args.seed)

		signature = inspect.signature(generator)
		kwargs, count = _parse_generator_args(args.args, signature)
		results = [generator(**kwargs) for _ in range(count)]
	except ValueError as exc:
		parser.error(str(exc))

	if args.format == "json":
		json.dump(results, sys.stdout, default=str)
		sys.stdout.write("\n")
		return 0

	for result in results:
		for line in _iter_text_lines(result):
			print(line)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
