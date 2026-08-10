VERSION := $(shell cat VERSION)
PACKAGE := git-exposure-auditor-v$(VERSION)

.PHONY: test syntax install package clean

test:
	bash tests/run_all.sh

syntax:
	bash tests/syntax.sh

install:
	bash install.sh

package: clean test
	cd .. && zip -qr $(PACKAGE).zip $(PACKAGE)
	cd .. && tar -czf $(PACKAGE).tar.gz $(PACKAGE)

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
