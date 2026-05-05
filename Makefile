.PHONY: paper clean

paper:
	latexmk -pdf -cd -interaction=nonstopmode -halt-on-error paper/agent_legible_repositories.tex

clean:
	latexmk -C -cd paper/agent_legible_repositories.tex
