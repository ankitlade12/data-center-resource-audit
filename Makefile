PYTHON ?= python3

.PHONY: diagnostics test-core acquire verify-sources rebuild test

diagnostics:
	$(PYTHON) src/analyze.py
	$(PYTHON) src/experiments.py
	$(PYTHON) src/resource_experiments.py
	$(PYTHON) src/robustness.py
	$(PYTHON) src/revision_diagnostics.py
	$(PYTHON) src/additional_capacity_diagnostics.py
	$(PYTHON) src/capacity_figure.py

test-core:
	$(PYTHON) -m unittest discover -s tests -p 'test_resources.py'
	$(PYTHON) -m unittest discover -s tests -p 'test_external_evidence.py'
	$(PYTHON) -m unittest discover -s tests -p 'test_revision_diagnostics.py'
	$(PYTHON) -m unittest discover -s tests -p 'test_acquire.py'

acquire:
	$(PYTHON) src/acquire.py

verify-sources:
	$(PYTHON) src/acquire.py --verify

rebuild:
	$(PYTHON) src/build_data.py
	$(PYTHON) src/meta_data.py
	$(PYTHON) src/spatial_data.py
	$(PYTHON) src/analyze.py
	$(PYTHON) src/experiments.py
	$(PYTHON) src/report.py
	$(PYTHON) src/resource_experiments.py
	$(PYTHON) src/local_constraints.py
	$(PYTHON) src/resource_report.py
	$(PYTHON) src/evidence_validation.py
	$(PYTHON) src/robustness.py
	$(PYTHON) src/revision_diagnostics.py
	$(PYTHON) src/additional_capacity_diagnostics.py
	$(PYTHON) src/capacity_figure.py

test:
	$(PYTHON) -m unittest discover -s tests -v
