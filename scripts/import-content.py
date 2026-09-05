#!/usr/bin/env python3
"""Import the original production Markdown, preserving source content and JSX.

Run: python3 scripts/import-content.py
Pages are fetched concurrently and cached so interrupted imports can resume.
"""
import concurrent.futures
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / 'provenance' / 'markdown'
METADATA = json.loads((ROOT / 'provenance/page-metadata.json').read_text())
EXPORT = (ROOT / 'provenance/llms-full.txt').read_text()
EXPORT_ROUTES = re.findall(r'^Source: https://docs\.replit\.com/(\S+)', EXPORT, re.M)
SITEMAP = ROOT / 'provenance/sitemap.xml'
SITEMAP_ROUTES = re.findall(r'<loc>https://docs\.replit\.com/(.*?)</loc>', SITEMAP.read_text()) if SITEMAP.exists() else []
ROUTES = list(dict.fromkeys([*METADATA, *EXPORT_ROUTES, *SITEMAP_ROUTES]))
MISSING_ONLY = '--missing-only' in sys.argv


def import_page(route):
    source = f'https://docs.replit.com/{route}.md'
    cached = CACHE / (route + '.md.txt')
    target = ROOT / (route + '.mdx')
    cached.parent.mkdir(parents=True, exist_ok=True)
    if not cached.exists():
        result = subprocess.run(['curl', '-L', '--fail', '--silent', '--show-error',
                                 '--retry', '3', '--max-time', '90', source, '-o', str(cached)],
                                capture_output=True, text=True)
        if result.returncode:
            return {'route': route, 'source': source, 'error': result.stderr.strip()}
    original = cached.read_text()
    if original.lstrip().startswith('<!DOCTYPE'):
        return {'route': route, 'source': source, 'error': 'Endpoint returned HTML'}
    body = re.sub(r'^> ## Documentation Index\n(?:>[^\n]*\n)*\n', '', original)
    title_match = re.match(r'^# ([^\n]+)\n+', body)
    title = title_match.group(1) if title_match else route.rsplit('/', 1)[-1]
    if title_match:
        body = body[title_match.end():]
    description = None
    if body.startswith('> '):
        description, _, body = body[2:].partition('\n')
        body = body.lstrip('\n')
    frontmatter = {'title': title}
    if description:
        frontmatter['description'] = description
    frontmatter.update(METADATA.get(route, {}))
    if frontmatter.pop('hiddenSetByFrontmatter', False):
        frontmatter['hidden'] = True
    serialized = '\n'.join(f'{key}: {json.dumps(value, ensure_ascii=False)}'
                           for key, value in frontmatter.items())
    result = f'---\n{serialized}\n---\n\n{body.rstrip()}\n'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not (MISSING_ONLY and target.exists()):
        target.write_text(result)
    return {'route': route, 'source': source,
            'sourceSha256': hashlib.sha256(original.encode()).hexdigest(),
            'sourceBytes': len(original.encode()), 'outputBytes': len(result.encode()),
            'inFullExport': route in EXPORT_ROUTES, 'inNavigation': route in METADATA,
            'inSitemap': route in SITEMAP_ROUTES}


def main():
    manifest = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for index, entry in enumerate(pool.map(import_page, ROUTES), 1):
            manifest.append(entry)
            if 'error' in entry:
                print(f"ERROR {entry['route']}: {entry['error']}", flush=True)
            elif index % 50 == 0:
                print(f'Imported {index}/{len(ROUTES)}', flush=True)
    failures = [entry for entry in manifest if 'error' in entry]
    (ROOT / 'provenance/content-manifest.json').write_text(json.dumps({
        'origin': 'https://docs.replit.com', 'exportPageCount': len(EXPORT_ROUTES),
        'navigationPageCount': len(METADATA), 'sitemapPageCount': len(SITEMAP_ROUTES),
        'importedPageCount': len(manifest) - len(failures),
        'pages': manifest}, indent=2) + '\n')
    print(f'Imported {len(manifest) - len(failures)} pages; {len(failures)} failures', flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
