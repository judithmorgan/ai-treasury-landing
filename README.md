# AI Treasury — Landing Page

Landing page for AI Treasury, an AI-powered treasury and cash management
platform for small-to-mid-sized businesses. Served by a small Python
backend that also powers an on-page FAQ chat assistant backed by Claude.

## What's here

- `index.html` — the landing page (single self-contained file, inline CSS)
- `server.py` — serves `index.html` and exposes `POST /api/chat`, which
  proxies chat messages to Claude using the business info in `CLAUDE.md`
  as its knowledge base
- `CLAUDE.md` — brand voice and business details (pricing, plans, policies)
  used both by Claude Code and by the chat assistant's system prompt

## Requirements

- Python 3.9+
- The [`anthropic`](https://pypi.org/project/anthropic/) Python SDK

Install the SDK:

```bash
pip install anthropic
```

## Setup

1. Get an API key from the [Anthropic Console](https://console.anthropic.com/).
2. Set it as an environment variable (never commit it to the repo):

   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

3. Run the server:

   ```bash
   python3 server.py
   ```

4. Open [http://localhost:8123](http://localhost:8123) in your browser.

By default the server runs on port `8123`. Override it with the `PORT`
environment variable:

```bash
PORT=3000 python3 server.py
```

If `ANTHROPIC_API_KEY` isn't set, the page still loads — the chat
assistant will just reply with a message pointing visitors to
support@aitreasury.com instead of calling Claude.

## Notes

- The chat assistant's knowledge is generated from `CLAUDE.md` at server
  startup, so keep pricing/plan details there up to date.
- No secrets are stored in code — the API key is read from the environment
  only.
