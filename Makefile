.PHONY: paper gate-test clean

paper:
	latexmk -pdf -cd -interaction=nonstopmode -halt-on-error paper/agent_legible_repositories.tex

gate-test:
	python3 -I templates/completion-gate/gate.py --self-test

clean:
	latexmk -C -cd paper/agent_legible_repositories.tex
