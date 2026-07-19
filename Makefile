PY := PYTHONPATH=src python

pilot:
	$(PY) -m govscore.cli pilot

test:
	PYTHONPATH=src pytest tests/ -q

extract:
	$(PY) -m govscore.cli extract --repo $(REPO)

.PHONY: pilot test extract
