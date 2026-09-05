#!/usr/bin/env python3
"""Inspect production redirect destinations for authored internal links."""
import concurrent.futures
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
missing = set()
for page in ROOT.rglob('*.mdx'):
    if 'node_modules' in page.parts:
        continue
    for target in re.findall(r'(?:href=["\']|\]\()(/[^\s"\')#]+)', page.read_text()):
        target = target.split('?')[0].rstrip('/')
        if target and not ((ROOT / (target[1:] + '.mdx')).exists() or (ROOT / target[1:]).exists()):
            missing.add(target)


def resolve(route):
    result = subprocess.run(['curl', '-L', '--silent', '--show-error', '--max-time', '60',
                             '-o', '/dev/null', '-w', '%{http_code}\t%{url_effective}',
                             'https://docs.replit.com' + route], text=True, capture_output=True)
    status, _, final_url = result.stdout.partition('\t')
    return {'source': route, 'status': status, 'destination': final_url,
            **({'error': result.stderr.strip()} if result.returncode else {})}


with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    results = list(pool.map(resolve, sorted(missing)))
target = ROOT / 'provenance/link-resolution.json'
target.write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
