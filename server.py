#!/usr/bin/env python3
"""AI Treasury landing page + chat backend.

Serves the static site AND a POST /api/chat endpoint that proxies to Claude.
The Anthropic API key is read from the ANTHROPIC_API_KEY environment variable
and never reaches the browser. Pure standard library apart from the (already
installed) `anthropic` SDK.

Run:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 server.py            # serves on http://localhost:8123
"""

import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

MODEL = "claude-haiku-4-5"
MAX_BODY_BYTES = 64 * 1024      # reject oversized request bodies
MAX_MESSAGES = 20               # cap conversation length
MAX_CONTENT_CHARS = 4000        # cap each message's length
MAX_TOKENS = 1024               # short FAQ-style answers

# --- System prompt, built once from CLAUDE.md ---------------------------------

_BRAND_INSTRUCTIONS = """You are the assistant for AI Treasury's website. \
Answer visitor questions about AI Treasury using ONLY the business information \
below.

Voice:
- Clear, confident, and trustworthy — write like a knowledgeable advisor, not a corporate brand.
- Use contractions ("you're", "it's", "let's"). Prefer short sentences.
- Avoid financial jargon; explain any necessary term in plain language.
- Lead with the benefit. No fear-based or "you're doing it wrong" framing.

Rules:
- Only answer questions about AI Treasury (its product, plans, pricing, policies, onboarding, and support).
- If a question is off-topic, or the answer isn't in the information below, say so briefly and point the visitor to support@aitreasury.com.
- Never invent pricing, features, or policies that aren't stated below.
- Keep answers concise — a few sentences is usually plenty.

--- AI TREASURY BUSINESS INFORMATION ---
"""


def _build_system_prompt():
    """Read CLAUDE.md so the assistant's knowledge stays in sync with the file."""
    here = os.path.dirname(os.path.abspath(__file__))
    claude_md = os.path.join(here, "CLAUDE.md")
    try:
        with open(claude_md, "r", encoding="utf-8") as f:
            business_info = f.read()
    except OSError:
        business_info = (
            "AI Treasury is an AI-powered treasury and cash management platform "
            "for small-to-mid-sized businesses. For details, contact "
            "support@aitreasury.com."
        )
    return _BRAND_INSTRUCTIONS + business_info


SYSTEM_PROMPT = _build_system_prompt()


# --- Request handler ----------------------------------------------------------

class Handler(SimpleHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/api/chat":
            self._send_json(404, {"error": "Not found."})
            return

        # --- Read + validate the request body ---
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "Please send a valid message."})
            return

        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "Please send a valid message."})
            return

        messages = self._clean_messages(data.get("messages"))
        if not messages:
            self._send_json(400, {"error": "Please send a message to get started."})
            return

        # --- Call Claude ---
        try:
            import anthropic
        except ImportError:
            self._send_json(200, {"error": "The assistant isn't available right now. Please email support@aitreasury.com."})
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            self._send_json(200, {"error": "The assistant isn't configured yet. Please email support@aitreasury.com and we'll be glad to help."})
            return

        try:
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            reply = next((b.text for b in resp.content if b.type == "text"), "")
            if not reply:
                reply = "Sorry, I didn't catch that. Could you rephrase, or email support@aitreasury.com?"
            self._send_json(200, {"reply": reply})
        except anthropic.AuthenticationError as e:
            print("ANTHROPIC AUTH ERROR:", e)
            self._send_json(200, {"error": "The assistant isn't configured correctly. Please email support@aitreasury.com."})
        except anthropic.APIError as e:
            print("ANTHROPIC API ERROR:", type(e).__name__, "-", e)
            self._send_json(200, {"error": "The assistant is having trouble right now. Please try again in a moment, or email support@aitreasury.com."})
        except Exception as e:
            print("UNEXPECTED ERROR:", type(e).__name__, "-", e)
            self._send_json(200, {"error": "Something went wrong. Please try again, or email support@aitreasury.com."})

    @staticmethod
    def _clean_messages(raw):
        """Validate/normalize the conversation: user/assistant only, alternating
        is not required by the API but the last turn must be from the user."""
        if not isinstance(raw, list):
            return None
        cleaned = []
        for item in raw[-MAX_MESSAGES:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in ("user", "assistant") or not isinstance(content, str):
                continue
            content = content.strip()[:MAX_CONTENT_CHARS]
            if content:
                cleaned.append({"role": role, "content": content})
        if not cleaned or cleaned[-1]["role"] != "user":
            return None
        return cleaned

    def log_message(self, *args):  # keep the console quiet
        pass


def main():
    port = int(os.environ.get("PORT", "8123"))
    server = ThreadingHTTPServer(("", port), Handler)
    key_state = "set" if os.environ.get("ANTHROPIC_API_KEY") else "NOT set (chat will return a setup message)"
    print("AI Treasury server running on http://localhost:%d" % port)
    print("ANTHROPIC_API_KEY: %s" % key_state)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
