SOURCES     = $(wildcard src/py/fake/*.py)
DOC_SOURCES = $(wildcard docs/* docs/*/*)
MANIFEST    = $(SOURCES) $(wildcard *.py api/*.* AUTHORS* README* LICENSE*)
VERSION     = `grep VERSION src/py/fake/__init__.py | cut -d '=' -f2  | xargs echo`
PRODUCT     = MANIFEST doc
OS          = `uname -s | tr A-Z a-z`

.PHONY: all doc clean check tests

all: $(PRODUCT)

release: $(PRODUCT)
	git commit -a -m "Release $(VERSION)" ; true
	git tag $(VERSION) ; true
	git push --all ; true
	python3.14 setup.py clean sdist

tests:
	PYTHONPATH=src/py:$(PYTHONPATH) python3.14 tests/$(OS)/all.py

clean:
	@rm -rf api/ build dist MANIFEST ; true

check:
	pychecker -100 $(SOURCES)

test:
	python3.14 tests/all.py

MANIFEST: $(MANIFEST)
	echo $(MANIFEST) | xargs -n1 | sort | uniq > $@

src/py/fake/data/topics.json: src/py/fake/text/topics.txt
	python3.14 -c "import json;print(json.dumps([_.strip() for _ in open('$<').readlines() if _.strip() and _.strip()[0] != '#']))" > "$@"

#EOF
