.PHONY: paper gate-test check clean

paper:
	latexmk -pdf -cd -interaction=nonstopmode -halt-on-error paper/agent_legible_repositories.tex

gate-test:
	python3 -I templates/completion-gate/gate.py --self-test

check: gate-test
	python3 -I scripts/check_repo.py
	@if command -v latexmk >/dev/null 2>&1; then $(MAKE) --no-print-directory paper; else echo "latexmk not found; skipping the paper build (CI builds it)"; fi

clean:
	latexmk -C -cd paper/agent_legible_repositories.tex
