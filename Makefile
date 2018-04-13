.PHONY: test all

# Find current git tag or commit id

REL:=$(shell git describe --always --tags --exact-match || git log --pretty=format:'%h' -n 1)
CURRBRANCH:=$(shell git rev-parse --abbrev-ref HEAD)

all: test dist

test:
	PYTHONPATH="./aws:${PYTHONPATH}" py.test test

dbg:
	@echo "REL $(REL)"
	@echo "CURRBRANCH $(CURRBRANCH)"

dist-reader: temp_reader-$(REL).tar.gz

temp_reader-$(REL).tar.gz: reader/*
	rm -rf .dist
	mkdir .dist
	rsync -rv --exclude "*~" --exclude __pycache__ reader/read_temp.py reader/crontab keys/publisher_key.json reader/read_temp_config.ini .dist/
	tar cz --transform="s/\.dist/temp_reader-$(REL)/" -f $@ .dist

dist-lambda:
	$(MAKE) aws


