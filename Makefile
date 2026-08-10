.PHONY: test syntax install package clean

test:
	./tests/run_all.sh

syntax:
	./tests/syntax.sh

install:
	./install.sh

package: clean test
	cd .. && zip -qr git-exposure-auditor-v3.2.0-rc1.zip git-exposure-auditor-v3.2.0-rc1
	cd .. && tar -czf git-exposure-auditor-v3.2.0-rc1.tar.gz git-exposure-auditor-v3.2.0-rc1

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
