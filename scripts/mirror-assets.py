#!/usr/bin/env python3
"""Mirror documentation media without changing their bytes or losing provenance."""
import concurrent.futures
import hashlib
import json
import pathlib
import re
import subprocess
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / 'verification' / 'assets.json'
MEDIA = re.compile(r'\.(?:avif|gif|ico|jpe?g|png|svg|webp|mp4|webm|mov|pdf|woff2?)(?:[?#]|$)', re.I)
URL = re.compile(r'https?://[^\s<>"\'`)}\\]+')
LOCAL = re.compile(r'(?<=["\'(])/(?:images|assets|videos|public)/[^\s<>"\'`)}\\]+')
HOSTS = {'docs.replit.com', 'mintcdn.com', 'cdn.replit.com', 'replit.com'}


def documents():
    return sorted([*ROOT.rglob('*.mdx'), ROOT / 'docs.json', ROOT / 'styles.css'])


def destination(url):
    parsed = urllib.parse.urlsplit(url)
    name = pathlib.PurePosixPath(urllib.parse.unquote(parsed.path)).name or 'asset'
    name = re.sub(r'[^A-Za-z0-9._-]', '-', name)
    stem, suffix = pathlib.PurePosixPath(name).stem, pathlib.PurePosixPath(name).suffix
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    return f'/assets/mirror/{stem}-{digest}{suffix}'


def download(item):
    url, record = item
    target = ROOT / record['local'].lstrip('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or not target.stat().st_size:
        temporary = target.with_name(target.name + '.download')
        result = subprocess.run(['curl', '-L', '--fail', '--silent', '--show-error',
                                 '--retry', '2', '--max-time', '120', url, '-o', str(temporary)],
                                capture_output=True, text=True)
        if result.returncode:
            temporary.unlink(missing_ok=True)
            return url, {**record, 'status': 'failed', 'error': result.stderr.strip()}
        temporary.replace(target)
    payload = target.read_bytes()
    if payload.lstrip().startswith((b'<!DOCTYPE html', b'<html')):
        target.unlink()
        return url, {**record, 'status': 'failed', 'error': 'Server returned HTML instead of media'}
    return url, {**record, 'status': 'downloaded', 'bytes': len(payload),
                 'sha256': hashlib.sha256(payload).hexdigest()}


def main():
    previous = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    records = previous.get('assets', {})
    external = set(previous.get('externalMedia', []))
    replacements = {}
    sources = {}
    for file in documents():
        if 'node_modules' in file.parts or 'snippets' in file.parts:
            continue
        text = file.read_text()
        sources[file] = text
        for raw in set(URL.findall(text)) | set(LOCAL.findall(text)):
            raw = raw.rstrip(',;')
            try:
                url = urllib.parse.urljoin('https://docs.replit.com', raw)
            except ValueError:
                continue  # Example URLs in code blocks can contain placeholders.
            url = url.replace('&amp;', '&')
            if not MEDIA.search(url):
                continue
            host = urllib.parse.urlsplit(url).hostname
            if host not in HOSTS:
                external.add(url)
                continue
            if raw.startswith('/assets/mirror/'):
                continue
            records.setdefault(url, {'local': destination(url), 'references': []})
            relative = file.relative_to(ROOT).as_posix()
            if relative not in records[url]['references']:
                records[url]['references'].append(relative)
            replacements[raw] = url
    print(f'Mirroring {len(records)} media assets; {len(external)} external media URLs retained.', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for index, (url, record) in enumerate(pool.map(download, records.items()), 1):
            records[url] = record
            if index % 50 == 0 or index == len(records):
                print(f'{index}/{len(records)} assets processed', flush=True)
    # Long URLs first prevent a base URL replacement from breaking srcset variants.
    ordered = sorted(replacements, key=len, reverse=True)
    changed = 0
    for file, source in sources.items():
        text = source
        for raw in ordered:
            record = records[replacements[raw]]
            if record['status'] == 'downloaded':
                text = text.replace(raw, record['local'])
        if text != source:
            file.write_text(text)
            changed += 1
    failed = [url for url, record in records.items() if record['status'] != 'downloaded']
    report = {'source': 'https://docs.replit.com', 'downloaded': len(records)-len(failed),
              'failed': failed, 'externalMedia': sorted(external),
              'bytes': sum(r.get('bytes', 0) for r in records.values()), 'assets': records}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(f"Updated {changed} files; {report['downloaded']} assets downloaded; {len(failed)} failures.", flush=True)
    if failed:
        print('\n'.join(f'{url}: {records[url]["error"]}' for url in failed), flush=True)


if __name__ == '__main__':
    main()
