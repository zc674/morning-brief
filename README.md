# Morning Brief

Every morning this agent searches today's news with Claude, writes a 3-minute
radio-style briefing, voices it as an MP3, and publishes it to a private-ish
URL. Your iPhone plays it the moment you stop your alarm.

```
GitHub Actions (6:15am) → brief.py → Claude + web search → script
                                    → OpenAI TTS → briefing.mp3 → GitHub Pages
iPhone: alarm stopped → Shortcut downloads briefing.mp3 → plays it
```

## How the agent works

Each run, Claude works in a loop and decides for itself what to do next:

1. **Research:** it searches the web, opens full articles when a snippet isn't
   enough, and calls `get_market_quotes` (live Yahoo Finance data, see `market.py`)
   for every market number it plans to say.
2. **Fact-check:** it reviews its own draft against what it retrieved, re-checks
   anything doubtful, and fixes or cuts it. The Actions log lists every search,
   article and quote it used, plus what the fact-check changed.
3. The final script is voiced and published, with a **Sources** list on the page.

Optional variables: `MAX_SEARCHES` (default 10), `MAX_FETCHES` (default 6),
`FACT_CHECK` (`0` to skip the review pass and save a little time and money).

## 1. Get two API keys (~5 min)

| Key | Where | Rough cost |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys (add a few dollars of credit) | a few cents/day (tokens + ~$0.01/search, 8 searches max) |
| `OPENAI_API_KEY` | platform.openai.com → API keys | ~1–2¢/day for 3 minutes of audio |

Expect roughly **$2–5 a month** total. Set a spending limit on both consoles.

## 2. Put the code on GitHub (~5 min)

1. Create a new repository on github.com (e.g. `morning-brief`). Public is
   free for Pages; private repos need a paid plan for Pages.
2. Upload these files, keeping the folder layout:
   `brief.py`, `requirements.txt`, `.github/workflows/morning-brief.yml`
   (on the web: **Add file → Upload files**; drag the whole folder in).
3. **Settings → Secrets and variables → Actions → Secrets**: add
   `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.
4. Same page, **Variables** tab (all optional):
   - `BRIEF_NAME` – your first name
   - `BRIEF_CITY` – e.g. `Chicago, IL` (adds a weather line)
   - `BRIEF_TIMEZONE` – e.g. `America/Chicago`
   - `BRIEF_TOPICS` – e.g. `world news, NYC local news, tech, the Knicks`
   - `BRIEF_SOURCES` – only search these sites, comma-separated (see below).
     Leave empty to search the whole web.
   - `BRIEF_MINUTES` – length, default `3`
   - `TTS_VOICE` – `marin` (default), `cedar`, `coral`, … (try them at openai.fm)
5. **Settings → Pages → Build and deployment → Source: GitHub Actions**.
6. **Actions tab → Morning brief → Run workflow** to test it now. After ~1–2
   minutes your briefing is at
   `https://<your-username>.github.io/morning-brief/` and the audio at
   `https://<your-username>.github.io/morning-brief/briefing.mp3`.

### Changing the time
Edit the `cron:` line in `.github/workflows/morning-brief.yml`. It's in **UTC**
and GitHub can start runs 10–30 minutes late, so schedule about an hour before
your alarm. Examples: `15 10 * * *` = 5:15am Chicago / 6:15am New York
(summer). Use https://crontab.guru to check.

### Example: a finance briefing
- `BRIEF_TOPICS`: `markets: how U.S. stocks closed yesterday and where futures are pointing, the Fed and interest rates, major earnings and company news, key economic data out today, oil, the dollar and crypto`
- `BRIEF_SOURCES` (optional): `reuters.com,apnews.com,cnbc.com,marketwatch.com,finance.yahoo.com,bloomberg.com,wsj.com,ft.com,federalreserve.gov`

Paywalled sites (Bloomberg, WSJ, FT) often only show headlines and snippets
to the search tool, so keep a few open sites (Reuters, AP, CNBC, Yahoo Finance)
in the list. A very short list can leave the agent with too little to work with.

### Optional: use your paid subscriptions (WSJ, Bloomberg, FT…) via newsletters
Web search only sees headlines and snippets from paywalled sites. Your
subscription's email newsletters contain the full text, so the agent can read
the last 24 hours of them from your mailbox. It reads without changing
anything: nothing is deleted, moved, or marked as read.

1. **Sign up for the newsletters** with your NYU address in each site's account
   settings. For example: WSJ *The 10-Point* and *Markets A.M.*; Bloomberg
   *Five Things* and *Markets Daily*; FT *FirstFT* and *Unhedged*.
2. **Create a Google app password for your NYU account.** Sign in at
   https://myaccount.google.com/apppasswords with your NYU email. You need
   Google 2-Step Verification turned on first (in **Security**). Name it
   "Morning brief" and copy the 16-character password.
   - If Google says *"The setting you are looking for is not available for
     your account,"* NYU has disabled app passwords. In that case, use a
     personal Gmail instead: subscribe the newsletters there, or forward them
     to it with a Gmail filter if NYU allows forwarding. Then create the app
     password on that account.
3. **Add two GitHub secrets:**
   - `NEWSLETTER_EMAIL`: e.g. `abc123@nyu.edu`
   - `NEWSLETTER_PASSWORD`: the app password (spaces are fine)
4. **Optional:** add a `NEWSLETTER_SENDERS` variable if you subscribe to other
   publications. The default covers
   `wsj.com,barrons.com,bloomberg.com,bloomberg.net,ft.com,economist.com`.

The Actions log lists which newsletters it found each morning. If the mailbox
can't be reached, the briefing still goes out using web search only.

**Notes:**
- An app password gives access to that whole mailbox. It's stored encrypted
  as a GitHub secret, and this code only reads mail from the listed senders.
  You can revoke it anytime on the same Google page.
- Your briefing page and MP3 can be opened by anyone who has the link. The
  agent summarizes the newsletters in its own words rather than quoting them,
  but don't share the link if you'd rather keep it to yourself.

## 3. Make the iPhone play it when your alarm stops (~3 min)

Shortcuts app → **Automation** → **+** → **Alarm** → **Is Stopped** → pick
your alarm (or Any) → **Run Immediately** → **New Blank Automation**, then add:

1. **Get Contents of URL** → `https://<your-username>.github.io/morning-brief/briefing.mp3?d=` +
   insert the **Current Date** variable at the end (stops your phone using
   yesterday's cached copy).
2. **Set Volume** → 60% (optional).
3. **Play Sound** → input: *Contents of URL*.

Turn off **Notify When Run**. Test it by setting an alarm one minute ahead.

**Text-only fallback** (no OpenAI key): use `.../briefing.txt` in step 1, and
**Speak Text** instead of Play Sound. Free, but the voice is Siri's.

**Android:** Tasker → Event "Alarm Done" → HTTP Request (download the MP3)
→ Media → Music Play.

## Troubleshooting
- **Actions run failed** → open the run log; a missing secret or no API
  credit is the usual cause.
- **Same briefing two days in a row** → the cache-busting `?d=` step is missing,
  or the morning run failed (check Actions).
- **Scheduled runs stopped** → GitHub pauses schedules in repos with no
  activity for 60 days; click "Enable workflow" in the Actions tab.
- The briefing is AI-written from search results; it can occasionally get a
  detail wrong. The web page lists today's script so you can check.
