#!/usr/bin/env python3
"""Rebuild the bundled examples with the current Python environment."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('names', nargs='*', help='Example folder names; defaults to all')
    args = p.parse_args()
    folders = [ROOT/'examples'/n for n in args.names] if args.names else sorted((ROOT/'examples').iterdir())
    for folder in folders:
        if not folder.is_dir():
            continue
        recipe = json.loads((folder/'recipe.json').read_text(encoding='utf-8'))
        cmd = [sys.executable, str(ROOT/'scripts/render_cover.py'), '--main', str(folder/'background.jpg'),
               '--output', str(folder/'cover.jpg')]
        for key, value in recipe.items():
            cmd += ['--'+key.replace('_','-'), str(value)]
        if (folder/'layout.json').exists():
            cmd += ['--collage', str(folder/'layout.json')]
        subprocess.run(cmd, check=True)
        print(folder.name)

if __name__ == '__main__':
    main()
