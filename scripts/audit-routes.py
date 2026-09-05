#!/usr/bin/env python3
"""Audit every imported route against a running local Mintlify preview."""
import concurrent.futures
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3011'
MANIFEST = json.loads((ROOT / 'provenance/content-manifest.json').read_text())
ROUTES = [p['route'] for p in MANIFEST['pages'] if 'error' not in p]
ERROR_PATTERNS = [
    r'Expected component [`&quot;]+([^`&]+)',
    r'ReferenceError: ([^<\\]{1,160})',
    r'Error evaluating MDX',
    r'There was an error loading this page',
    r'<title>[^<]*(?:404|Page not found|Error)[^<]*</title>',
]


def audit(route):
    started = time.monotonic()
    result = {'route': route}
    try:
        with urllib.request.urlopen(BASE.rstrip('/') + '/' + route, timeout=120) as response:
            html = response.read().decode()
            result['status'] = response.status
            result['bytes'] = len(html.encode())
            result['errors'] = [match.group(0)[:200] for pattern in ERROR_PATTERNS
                                for match in re.finditer(pattern, html)]
            if 'id="content-area"' not in html:
                result['errors'].append('Missing rendered content area')
    except Exception as error:
        result['error'] = str(error)
    result['seconds'] = round(time.monotonic() - started, 2)
    return result


def main():
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for index, result in enumerate(executor.map(audit, ROUTES), 1):
            results.append(result)
            if result.get('error') or result.get('errors'):
                print(json.dumps(result, ensure_ascii=False), flush=True)
            elif index % 100 == 0:
                print(f'Audited {index}/{len(ROUTES)}', flush=True)
    failures = [r for r in results if r.get('error') or r.get('errors')]
    target = ROOT / 'verification/route-audit.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps({'baseUrl': BASE, 'routeCount': len(results),
                                 'failureCount': len(failures), 'routes': results}, indent=2) + '\n')
    print(f'{len(results)} routes checked; {len(failures)} failures', flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
