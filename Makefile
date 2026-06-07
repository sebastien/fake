SOURCES          = $(wildcard src/py/fake/*.py)
MANIFEST_SOURCES = $(SOURCES) $(wildcard *.py api/*.* AUTHORS* README* LICENSE*)
MISE             = mise exec --
VERSION          = `grep VERSION src/py/fake/__init__.py | cut -d '=' -f2 | xargs echo`
PRODUCT          = MANIFEST

.PHONY: all release tests test clean check mise-trust

mise-trust:
	@mise trust -q -y "$(CURDIR)/mise.toml" >/dev/null 2>&1 || true

all: mise-trust $(PRODUCT)

release: mise-trust $(PRODUCT)
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	$(MISE) python setup.py clean sdist

tests test: mise-trust
	PYTHONPATH=src/py:$(PYTHONPATH) $(MISE) python test.py

clean:
	@rm -rf api/ build dist MANIFEST ; true

check: mise-trust
	PYTHONPATH=src/py:$(PYTHONPATH) $(MISE) python -m py_compile $(SOURCES) test.py setup.py

MANIFEST: mise-trust $(MANIFEST_SOURCES)
	$(MISE) python -c "import pathlib, sys; paths = sorted(set(sys.argv[2:])); pathlib.Path(sys.argv[1]).write_text(''.join(f'{path}\n' for path in paths), encoding='utf-8')" "$@" $(MANIFEST_SOURCES)

src/py/fake/data/topics.json: mise-trust src/py/fake/text/topics.txt
	$(MISE) python -c "import json, pathlib, sys; source = pathlib.Path(sys.argv[1]); target = pathlib.Path(sys.argv[2]); topics = [line.strip() for line in source.read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]; target.write_text(json.dumps(topics), encoding='utf-8')" "src/py/fake/text/topics.txt" "$@"

# EOF
