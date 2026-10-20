#!/usr/bin/env python3
"""Deterministic checks for this repository's written rules (see AGENTS.md).

- Every \\cite key resolves, keys are unique, and every bibliography entry is cited.
- Every @misc reference records an access date.
- No generated LaTeX files or machine-specific paths are committed.

Prints one line per problem and exits 1 if any are found.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / 'paper/agent_legible_repositories.tex'
BIB = ROOT / 'paper/references.bib'
GENERATED = re.compile(r'\.(aux|bbl|bcf|blg|fdb_latexmk|fls|log|out|run\.xml|synctex\.gz|toc|xdv|pdf)$')
# Split so this file does not match itself.
LOCAL_PATH = re.compile(r'/home/[a-z_][\w-]*/|/Users/[A-Za-z]\w*/|/tmp/' + 'claude|[A-Z]:\\\\Users\\\\')


def citation_problems():
    tex = PAPER.read_text(encoding='utf8')
    bib = BIB.read_text(encoding='utf8')
    cited = {k.strip() for group in re.findall(r'\\cite\{([^}]*)\}', tex) for k in group.split(',')}
    entries = re.findall(r'^@(\w+)\{([^,]+),(.*?)^\}', bib, re.M | re.S)
    keys = [key for _, key, _ in entries]
    problems = [f'{BIB.name}: duplicate key {k}' for k in sorted({k for k in keys if keys.count(k) > 1})]
    problems += [f'{PAPER.name}: \\cite{{{k}}} has no bibliography entry' for k in sorted(cited - set(keys))]
    problems += [f'{BIB.name}: {k} is never cited' for k in sorted(set(keys) - cited)]
    problems += [f'{BIB.name}: {key} (@misc) has no access date in its note'
                 for kind, key, body in entries
                 if kind.lower() == 'misc' and not re.search(r'note\s*=\s*\{[^}]*accessed', body, re.I)]
    return problems


def hygiene_problems():
    tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
    problems = []
    for name in (p.decode() for p in tracked.split(b'\0') if p):
        path = ROOT / name
        if GENERATED.search(name):
            problems.append(f'{name}: generated file is committed')
        elif path.is_file() and not path.is_symlink():
            text = path.read_text(encoding='utf8', errors='ignore')
            match = LOCAL_PATH.search(text)
            if match:
                problems.append(f'{name}: machine-specific path {match.group(0)!r}')
    return problems


def main():
    problems = citation_problems() + hygiene_problems()
    for problem in problems:
        print(f'ERROR {problem}')
    print(f'check_repo: {len(problems)} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
