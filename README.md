# Replit Docs — General Translation Demo

This repository is a **demo project**, not an official Replit product. It's a local
[Mintlify](https://mintlify.com) copy of [docs.replit.com](https://docs.replit.com),
used to demonstrate how [General Translation](https://generaltranslation.com) can
localize a real, production-scale Mintlify documentation site.

## What's here

- The full English content and navigation structure of Replit's public docs,
  imported from Replit's own per-page Markdown export. **English only** — no
  locales are configured or present.
- The mirrored `docs.json` theme, fonts, and styling, so the local preview looks
  like the production site (with a blue **(Demo)** badge added next to the logo
  to distinguish it from the real thing).
- `scripts/` and `verification/` — the tooling used to import content, mirror
  media assets, restore shared components, and check the local build against
  production for content and visual parity.

## Why it exists

This project exists purely to give General Translation a realistic, full-size,
**untranslated** Mintlify docs site to demo localization workflows against —
without needing write access to Replit's actual repository. Any translation
tooling (locale directories, `gt.config.json`, `gt-lock.json`, etc.) should be
set up fresh as part of a demo run rather than assumed to already exist here.

## Running locally

```bash
pnpm install
pnpm dev            # starts the Mintlify preview (mint dev)
pnpm validate        # validate docs.json / MDX
pnpm check:links     # check for broken links
```

## Attribution

All documentation content belongs to [Replit](https://replit.com) and is
mirrored here from their public docs site for demonstration purposes only.
This project is not affiliated with, endorsed by, or sponsored by Replit.
