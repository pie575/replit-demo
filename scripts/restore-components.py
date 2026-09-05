#!/usr/bin/env python3
"""Connect shared source exports omitted by Mintlify's markdown endpoints."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / 'snippets/shared-components.mdx'
NAMES = re.findall(r'^export const (\w+)', SHARED.read_text(), re.M)
modified = {}
for path in ROOT.rglob('*.mdx'):
    if 'node_modules' in path.parts or 'snippets' in path.parts:
        continue
    text = path.read_text()
    # Imports are regenerated, so a refresh is safe and deterministic.
    text = re.sub(r'^import \{[^\n]+\} from "/snippets/shared-components.mdx";\n\n', '', text, flags=re.M)
    needed = [name for name in NAMES if re.search(r'<' + name + r'\b', text)
              and not re.search(r'\b(?:const|function)\s+' + name + r'\b', text)]
    if needed:
        end = text.find('\n---\n', 4) + len('\n---\n') if text.startswith('---\n') else 0
        text = text[:end] + '\nimport { ' + ', '.join(needed) + ' } from "/snippets/shared-components.mdx";\n' + text[end:]
        modified[path.relative_to(ROOT).as_posix()] = needed
    if text != path.read_text():
        path.write_text(text)
report = ROOT / 'provenance/component-restoration.json'
data = json.loads(report.read_text())
data['pages'] = modified
report.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
print(f'Connected shared component exports on {len(modified)} pages.')
