"""
Read the last day's subscription newsletters (WSJ, Bloomberg, FT, ...) from
your mailbox over IMAP, read-only, so the briefing can use reporting that is
behind a paywall on the web.

Settings (environment variables):
  NEWSLETTER_EMAIL      the mailbox address, e.g. abc123@nyu.edu
  NEWSLETTER_PASSWORD   a Google *app password* (not your NetID password)
  NEWSLETTER_IMAP_HOST  default imap.gmail.com (NYU email is Google)
  NEWSLETTER_SENDERS    comma-separated sender domains/addresses to read
  NEWSLETTER_HOURS      how far back to look, default 24

Nothing is deleted, moved or marked as read.
"""

import datetime
import email
import html
import imaplib
import os
import re
from email.header import decode_header, make_header
from email.policy import default as default_policy
from html.parser import HTMLParser

DEFAULT_SENDERS = "wsj.com,barrons.com,bloomberg.com,bloomberg.net,ft.com,economist.com"
PER_EMAIL_CHARS = 6000   # keep each newsletter to a readable length
TOTAL_CHARS = 45000      # cap on everything passed to Claude
MAX_EMAILS = 12


class _TextExtractor(HTMLParser):
    """Turn newsletter HTML into plain text, skipping styles and scripts."""

    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "td"}

    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _html_to_text(raw_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_html)
    return html.unescape("".join(parser.parts))


def _clean(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t ‌͏]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    # Cut the boilerplate footer most newsletters end with.
    cut = re.search(r"(?im)^.*(unsubscribe|manage (your )?(email|newsletter)|privacy policy).*$", text)
    if cut and cut.start() > 500:
        text = text[: cut.start()]
    return text.strip()


def _body_text(msg) -> str:
    plain = msg.get_body(preferencelist=("plain",))
    rich = msg.get_body(preferencelist=("html",))
    text = ""
    if plain is not None:
        text = plain.get_content()
    # Many newsletters ship a stub plain-text part ("view in browser"); prefer HTML then.
    if rich is not None and len(text) < 800:
        text = _html_to_text(rich.get_content())
    return _clean(text)


def _decode(value) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def _search(conn, host, senders, since):
    if "gmail" in host:
        # Search all mail (newsletters often skip the inbox via filters/tabs).
        for box in ('"[Gmail]/All Mail"', '"[Google Mail]/All Mail"', "INBOX"):
            if conn.select(box, readonly=True)[0] == "OK":
                break
        hours = max(1, int((datetime.datetime.now(datetime.timezone.utc) - since).total_seconds() // 3600))
        query = f'from:({" OR ".join(senders)}) newer_than:{max(1, -(-hours // 24))}d'
        status, data = conn.search(None, "X-GM-RAW", f'"{query}"')
    else:
        conn.select("INBOX", readonly=True)
        crit = "(SINCE {})".format(since.strftime("%d-%b-%Y"))
        ors = [f'FROM "{s}"' for s in senders]
        while len(ors) > 1:  # IMAP OR is binary
            ors = [f"(OR {ors[0]} {ors[1]})"] + ors[2:]
        status, data = conn.search(None, f"({crit} {ors[0]})")
    return data[0].split() if status == "OK" and data and data[0] else []


def fetch_newsletters() -> list[dict]:
    user = os.environ.get("NEWSLETTER_EMAIL", "").strip()
    password = os.environ.get("NEWSLETTER_PASSWORD", "").replace(" ", "").strip()
    if not (user and password):
        return []
    host = os.environ.get("NEWSLETTER_IMAP_HOST", "imap.gmail.com")
    senders = [s.strip() for s in os.environ.get("NEWSLETTER_SENDERS", DEFAULT_SENDERS).split(",") if s.strip()]
    hours = int(os.environ.get("NEWSLETTER_HOURS", "24"))
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)

    conn = imaplib.IMAP4_SSL(host)
    try:
        conn.login(user, password)
        ids = _search(conn, host, senders, since)
        items = []
        for msg_id in reversed(ids[-MAX_EMAILS * 2:]):  # newest first
            # BODY.PEEK leaves the message unread.
            status, data = conn.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not data or not isinstance(data[0], tuple):
                continue
            msg = email.message_from_bytes(data[0][1], policy=default_policy)
            try:
                sent = email.utils.parsedate_to_datetime(msg["Date"])
                if sent.tzinfo and sent < since:
                    continue
            except Exception:
                pass
            body = _body_text(msg)
            if len(body) < 200:
                continue
            items.append({
                "from": _decode(msg["From"]),
                "subject": _decode(msg["Subject"]),
                "date": msg["Date"] or "",
                "text": body[:PER_EMAIL_CHARS],
            })
            if len(items) >= MAX_EMAILS:
                break
        return items
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def format_for_prompt(items: list[dict]) -> str:
    out, used = [], 0
    for it in items:
        block = (
            f'<newsletter from="{html.escape(it["from"])}" subject="{html.escape(it["subject"])}" '
            f'date="{html.escape(it["date"])}">\n{it["text"]}\n</newsletter>'
        )
        if used + len(block) > TOTAL_CHARS:
            break
        out.append(block)
        used += len(block)
    return "\n\n".join(out)
