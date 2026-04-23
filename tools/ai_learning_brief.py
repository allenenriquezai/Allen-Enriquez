"""
AI Learning Brief — Daily educational email.

One topic per day (mini-course) + expert digest from Anthropic, OpenAI, DeepMind, Hugging Face.
Fetches articles, summarises them via Claude Haiku, and delivers a self-contained
brief you can absorb in under 10 minutes — no clicking required.

Usage:
    python3 tools/ai_learning_brief.py              # generate data files only (no email)
    python3 tools/ai_learning_brief.py --send        # generate + send email
    python3 tools/ai_learning_brief.py --dry-run    # preview only, no files written
    python3 tools/ai_learning_brief.py --to x@y.com # override recipient (with --send)

Requires:
    projects/personal/token_personal_ai.pickle: Gmail OAuth token with send scope
    projects/personal/.env: ANTHROPIC_API_KEY
"""

import argparse
import base64
import json
import os
import pickle
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).parent.parent
SHARED_ENV = BASE_DIR / 'projects' / '.env'
PERSONAL_TOKEN = BASE_DIR / 'projects' / 'personal' / 'token_personal_ai.pickle'
PERSONAL_ENV = BASE_DIR / 'projects' / 'personal' / '.env'
TMP_DIR = BASE_DIR / '.tmp'

FROM_EMAIL = 'allenenriquez@gmail.com'
FROM_NAME = 'Enriquez OS'
TO_EMAIL_DEFAULT = 'allenenriquez.ai@gmail.com'


def load_env():
    for env_file in [SHARED_ENV, PERSONAL_ENV]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()

# --- 8-Week Curriculum: Beginner → Pro ---
# Each week has 7 daily lessons. Cycles after week 8 (day 56+).
# Start date = first run. Progress tracked in .tmp/learning_progress.json.

COURSE_START = datetime(2026, 4, 8)  # today

CURRICULUM = [
    # Week 1: Foundations — what AI actually is
    {'week': 1, 'theme': 'AI Foundations', 'lessons': [
        {'title': 'What Are Large Language Models?', 'query': 'what are large language models explained simply'},
        {'title': 'How ChatGPT & Claude Actually Work', 'query': 'how do ChatGPT Claude AI models work under the hood'},
        {'title': 'Tokens, Context Windows & Temperature', 'query': 'AI tokens context window temperature explained'},
        {'title': 'AI vs Machine Learning vs Deep Learning', 'query': 'AI vs machine learning vs deep learning difference explained'},
        {'title': 'What AI Can and Cannot Do (2026)', 'query': 'what can AI do what are AI limitations 2026'},
        {'title': 'The AI Landscape — Key Companies & Models', 'query': 'AI landscape OpenAI Anthropic Google Meta models 2026'},
        {'title': 'Week 1 Recap + What\'s Coming Next', 'query': 'getting started with AI practical guide beginner 2026'},
    ]},
    # Week 2: Prompt Engineering — talking to AI
    {'week': 2, 'theme': 'Prompt Engineering', 'lessons': [
        {'title': 'Your First Good Prompt — Structure Matters', 'query': 'how to write good AI prompts structure tips'},
        {'title': 'System Prompts — Setting the Rules', 'query': 'AI system prompts how to write examples'},
        {'title': 'Chain-of-Thought — Making AI Think Step by Step', 'query': 'chain of thought prompting technique examples'},
        {'title': 'Few-Shot Examples — Teaching by Showing', 'query': 'few-shot prompting examples AI technique'},
        {'title': 'Prompt Templates & Reusable Patterns', 'query': 'prompt templates reusable patterns AI automation'},
        {'title': 'Common Mistakes — What Not to Do', 'query': 'common prompt engineering mistakes to avoid'},
        {'title': 'Week 2 Recap — Build Your Prompt Library', 'query': 'prompt engineering best practices library 2026'},
    ]},
    # Week 3: Claude & the Anthropic Ecosystem
    {'week': 3, 'theme': 'Claude Deep Dive', 'lessons': [
        {'title': 'Claude vs GPT vs Gemini — When to Use What', 'query': 'Claude vs GPT vs Gemini comparison strengths 2026'},
        {'title': 'The Claude API — Your First API Call', 'query': 'Claude API getting started first call tutorial'},
        {'title': 'Claude Code — AI in Your Terminal', 'query': 'Claude Code CLI tool features how to use'},
        {'title': 'Tool Use — Letting Claude Call Functions', 'query': 'Claude tool use function calling tutorial'},
        {'title': 'Extended Thinking & Long Context', 'query': 'Claude extended thinking long context window how to use'},
        {'title': 'Anthropic\'s Safety Approach — Why It Matters', 'query': 'Anthropic AI safety constitutional AI approach'},
        {'title': 'Week 3 Recap — Claude Power User Tips', 'query': 'Claude AI power user tips advanced features 2026'},
    ]},
    # Week 4: Automation Tools — connecting the pieces
    {'week': 4, 'theme': 'Automation Tools', 'lessons': [
        {'title': 'No-Code Automation — Zapier, Make, n8n', 'query': 'Zapier vs Make vs n8n automation comparison 2026'},
        {'title': 'n8n Deep Dive — Self-Hosted Workflows', 'query': 'n8n self hosted automation workflows tutorial'},
        {'title': 'Connecting APIs — The Glue That Holds It Together', 'query': 'connecting APIs automation workflows REST webhooks'},
        {'title': 'Webhooks — Triggering Actions Automatically', 'query': 'webhooks explained how to use automation'},
        {'title': 'Scheduling & Cron Jobs — Running Things on Time', 'query': 'cron jobs scheduling automation launchd explained'},
        {'title': 'Python for Automation — Scripts That Do Work', 'query': 'Python automation scripts practical examples business'},
        {'title': 'Week 4 Recap — Your Automation Stack', 'query': 'best automation stack small business AI 2026'},
    ]},
    # Week 5: Agentic Workflows — AI that acts
    {'week': 5, 'theme': 'Agentic Workflows', 'lessons': [
        {'title': 'What Are AI Agents? (Not Just Chatbots)', 'query': 'what are AI agents vs chatbots explained 2026'},
        {'title': 'Agent Loops — Observe, Think, Act', 'query': 'AI agent loop observe think act pattern'},
        {'title': 'Multi-Agent Systems — Agents Working Together', 'query': 'multi agent AI systems orchestration patterns'},
        {'title': 'Agent Memory — Short-Term vs Long-Term', 'query': 'AI agent memory systems context persistence'},
        {'title': 'Error Handling & Self-Correction', 'query': 'AI agent error handling self correction retry patterns'},
        {'title': 'Human-in-the-Loop — When to Ask for Help', 'query': 'human in the loop AI agent design approval gates'},
        {'title': 'Week 5 Recap — Design Your First Agent', 'query': 'building AI agents practical guide beginner 2026'},
    ]},
    # Week 6: MCP & Tool Use — AI meets the real world
    {'week': 6, 'theme': 'MCP & Tool Use', 'lessons': [
        {'title': 'What Is MCP? (Model Context Protocol)', 'query': 'model context protocol MCP explained what is it'},
        {'title': 'MCP Servers — Giving AI Access to Tools', 'query': 'MCP servers setup tutorial AI tool access'},
        {'title': 'Building Your Own MCP Server', 'query': 'build custom MCP server tutorial Python'},
        {'title': 'Function Calling — The API Approach', 'query': 'AI function calling tool use API tutorial'},
        {'title': 'File Systems, Databases & External APIs', 'query': 'AI agent accessing files databases APIs patterns'},
        {'title': 'Security — Safe Tool Use in Production', 'query': 'AI agent security tool use permissions safety'},
        {'title': 'Week 6 Recap — Your Tool Use Playbook', 'query': 'AI tool use MCP best practices patterns 2026'},
    ]},
    # Week 7: Building AI Systems — putting it all together
    {'week': 7, 'theme': 'Building AI Systems', 'lessons': [
        {'title': 'Architecture — How to Structure an AI System', 'query': 'AI system architecture design patterns production'},
        {'title': 'Prompt Management — Version Control for Prompts', 'query': 'prompt management version control AI production'},
        {'title': 'Testing AI — How to Know It Works', 'query': 'testing AI systems evaluation metrics practical'},
        {'title': 'Cost Management — Keeping API Bills Low', 'query': 'AI API cost management optimization tips'},
        {'title': 'Monitoring & Logging — Watching Your Agents', 'query': 'AI agent monitoring logging observability production'},
        {'title': 'Scaling — From Prototype to Production', 'query': 'scaling AI prototype to production deployment'},
        {'title': 'Week 7 Recap — Your Production Checklist', 'query': 'AI system production readiness checklist 2026'},
    ]},
    # Week 8: AI Business Strategy — making money with AI
    {'week': 8, 'theme': 'AI Business Strategy', 'lessons': [
        {'title': 'Finding ROI — Where AI Saves Real Time', 'query': 'AI ROI small business where to automate first'},
        {'title': 'AI for Sales — CRM, Follow-ups, Lead Scoring', 'query': 'AI for sales automation CRM lead scoring 2026'},
        {'title': 'AI for Operations — Scheduling, Dispatch, Docs', 'query': 'AI operations automation scheduling documents'},
        {'title': 'Building an AI Consultancy', 'query': 'AI automation consultancy business model 2026'},
        {'title': 'Pricing AI Services — What to Charge', 'query': 'pricing AI automation services consulting rates'},
        {'title': 'The AI Agency Model — Pros & Cons', 'query': 'AI agency business model pros cons 2026'},
        {'title': 'Week 8 Recap — Your AI Business Plan', 'query': 'AI business strategy plan small business 2026'},
    ]},
]

EXPERTS = [
    {'name': 'Anthropic', 'query': 'Anthropic Claude AI latest news updates 2026'},
    {'name': 'OpenAI', 'query': 'OpenAI GPT latest news updates 2026'},
    {'name': 'Google DeepMind', 'query': 'Google DeepMind Gemini AI latest news 2026'},
    {'name': 'Hugging Face', 'query': 'Hugging Face open source AI models latest 2026'},
]


# --- Web search ---

def search_articles(query, max_results=5):
    """Search DuckDuckGo HTML and parse top results."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"    Search failed: {e}")
        return []

    title_pattern = re.compile(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL)
    snippet_pattern = re.compile(
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)

    titles = title_pattern.findall(html)
    snippets = snippet_pattern.findall(html)

    results = []
    for i in range(min(len(titles), len(snippets), max_results)):
        raw_url, raw_title = titles[i]
        raw_snippet = snippets[i]

        title = re.sub(r'<[^>]+>', '', raw_title).strip()
        snippet = re.sub(r'<[^>]+>', '', raw_snippet).strip()

        if 'uddg=' in raw_url:
            match = re.search(r'uddg=([^&]+)', raw_url)
            if match:
                raw_url = urllib.parse.unquote(match.group(1))

        if title and snippet:
            results.append({'title': title, 'snippet': snippet[:200], 'url': raw_url})

    return results


def fetch_page_text(url, max_chars=3000):
    """Fetch a web page and extract readable article text (best-effort)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception:
        return ''

    # Remove noise: scripts, styles, nav, header, footer, aside, forms, cookie banners
    cleaned = html
    for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'noscript']:
        cleaned = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', ' ', cleaned, flags=re.DOTALL)

    def strip_tags(s):
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s)).strip()

    # Strategy 1: <article> or <main> container
    article_match = re.search(r'<article[^>]*>(.*?)</article>', cleaned, re.DOTALL)
    main_match = re.search(r'<main[^>]*>(.*?)</main>', cleaned, re.DOTALL)
    content_html = article_match.group(1) if article_match else (
        main_match.group(1) if main_match else None)

    # Strategy 2: content divs with common class names
    if not content_html or len(strip_tags(content_html)) < 200:
        content_patterns = [
            r'<div[^>]*class="[^"]*(?:article-body|post-content|entry-content|blog-content|cms-richtext|rich-text|content-body|main-content)[^"]*"[^>]*>(.*?)</div>',
            r'<section[^>]*class="[^"]*(?:article|post|entry|content)[^"]*"[^>]*>(.*?)</section>',
        ]
        for pat in content_patterns:
            m = re.search(pat, cleaned, re.DOTALL)
            if m and len(strip_tags(m.group(1))) >= 200:
                content_html = m.group(1)
                break

    # Strategy 3: Extract <p> tags from best source
    source = content_html if content_html else cleaned
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', source, re.DOTALL)
    if paragraphs:
        p_text = ' '.join(strip_tags(p) for p in paragraphs if len(strip_tags(p)) > 20)
        if len(p_text) >= 200:
            return p_text[:max_chars]

    # Strategy 4: if we have a content container, use all its text
    if content_html:
        text = strip_tags(content_html)
        if len(text) >= 200:
            return text[:max_chars]

    # Strategy 5: <li> items (some articles use lists heavily)
    list_items = re.findall(r'<li[^>]*>(.*?)</li>', source, re.DOTALL)
    if list_items:
        li_text = ' '.join(strip_tags(li) for li in list_items if len(strip_tags(li)) > 15)
        if len(li_text) >= 200:
            return li_text[:max_chars]

    # Fallback: full text extraction from cleaned HTML
    text = strip_tags(cleaned)
    return text[:max_chars]


REFUSAL_MARKERS = [
    'i cannot complete this task',
    'i cannot provide an accurate summary',
    'i cannot provide a summary',
    'i cannot summarize',
    'the article text provided is incomplete',
    'the article text provided contains only',
    'the text provided appears to be',
    'i\'m unable to provide',
    'i don\'t have enough content',
    'no actual content',
]


def call_claude(prompt, max_tokens=1200):
    """Call Claude Haiku via the Anthropic Messages API."""
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key or api_key == 'your-key-here':
        print("    WARNING: No ANTHROPIC_API_KEY — falling back to snippets")
        return None

    body = json.dumps({
        'model': 'claude-haiku-4-5-20251001',
        'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode())
        text = resp['content'][0]['text']
        # Reject refusal responses — Claude couldn't summarize the content
        lower = text.lower()
        if any(marker in lower for marker in REFUSAL_MARKERS):
            print(f"    Claude refused (bad input) — skipping")
            return None
        return text
    except Exception as e:
        print(f"    Claude API error: {e}")
        return None


# --- Data fetchers ---

def fetch_mini_course():
    """Pick today's lesson, fetch articles, and summarise via Claude."""
    days_in = (datetime.now() - COURSE_START).days
    total_lessons = sum(len(w['lessons']) for w in CURRICULUM)
    day_index = days_in % total_lessons

    count = 0
    for week in CURRICULUM:
        for i, lesson in enumerate(week['lessons']):
            if count == day_index:
                week_num = week['week']
                theme = week['theme']
                day_num = i + 1
                label = f"Week {week_num}: {theme} — Day {day_num}/7"
                print(f"  [Mini Course] {label}")
                print(f"    Lesson: {lesson['title']}")
                articles = search_articles(lesson['query'])
                print(f"    Found {len(articles)} articles")

                # Fetch page text from top 3 articles
                source_text = ''
                for a in articles[:3]:
                    print(f"    Fetching: {a['title'][:50]}...")
                    page = fetch_page_text(a['url'])
                    if page:
                        source_text += f"\n--- {a['title']} ---\n{page}\n"

                # Summarise with Claude
                summary = None
                if source_text:
                    prompt = (
                        f"You are a teacher writing a mini-lesson for someone who knows "
                        f"nothing about tech or AI. Topic: \"{lesson['title']}\"\n\n"
                        f"Write like you are talking to a 10 year old. Use the simplest "
                        f"words you can. Short sentences. No big words.\n\n"
                        f"Write a lesson that teaches this topic from scratch:\n"
                        f"1. Start with a real-world analogy that makes the concept click.\n"
                        f"2. Explain how it works in 2-3 short paragraphs. Every paragraph "
                        f"should teach something new.\n"
                        f"3. Give 3 key takeaways as bullet points (use •).\n"
                        f"4. End with one \"Try This:\" action the reader can do today.\n\n"
                        f"Rules:\n"
                        f"- No jargon. If you must use a technical term, explain it right away.\n"
                        f"- Do NOT use markdown headers. Just paragraphs then bullets.\n"
                        f"- Keep the total under 300 words.\n\n"
                        f"SOURCE MATERIAL:\n{source_text[:4000]}"
                    )
                    print("    Summarising with Claude...")
                    summary = call_claude(prompt)

                if not summary:
                    # Fallback: use search snippets
                    summary = '\n'.join(
                        f"• {a['snippet']}" for a in articles[:3]
                    )

                progress = f"Day {days_in + 1} of {total_lessons}"
                if days_in >= total_lessons:
                    progress += " (cycle 2+)"
                return {
                    'title': lesson['title'],
                    'week_label': label,
                    'progress': progress,
                    'summary': summary,
                    'articles': articles,
                }
            count += 1

    return {'title': 'Rest Day', 'week_label': '', 'progress': '',
            'summary': '', 'articles': []}


def fetch_expert_digest():
    """Search for latest content from each expert, summarise via Claude."""
    digest = []
    all_source = ''
    for expert in EXPERTS:
        print(f"  [Expert] {expert['name']}")
        articles = search_articles(expert['query'], max_results=3)
        print(f"    Found {len(articles)} articles")

        # Gather snippets + page text from top article
        expert_text = ''
        for a in articles[:1]:
            page = fetch_page_text(a['url'], max_chars=1500)
            if page:
                expert_text = page
        if not expert_text:
            expert_text = ' '.join(a['snippet'] for a in articles[:3])

        all_source += f"\n--- {expert['name']} ---\n{expert_text}\n"
        digest.append({'name': expert['name'], 'articles': articles})

    # Single Claude call for all experts
    if all_source:
        prompt = (
            "Summarise what each AI company has been up to recently. "
            "For each company, write 1-2 sentences in plain English. "
            "Use simple words. Be specific about what they released or announced.\n"
            "Format: one line per company, starting with the company name in bold (**Name**).\n"
            "If the source material has no real news, say 'No major updates this week.'\n\n"
            f"SOURCE MATERIAL:\n{all_source[:6000]}"
        )
        print("    Summarising expert digest with Claude...")
        expert_summary = call_claude(prompt, max_tokens=500)
        if expert_summary:
            # Parse summary lines back to each expert
            for entry in digest:
                for line in expert_summary.split('\n'):
                    if entry['name'].lower() in line.lower():
                        entry['summary'] = re.sub(
                            r'\*\*[^*]+\*\*:?\s*', '', line
                        ).strip()
                        break
                if 'summary' not in entry:
                    entry['summary'] = ''

    # Fallback for any missing summaries
    for entry in digest:
        if 'summary' not in entry or not entry['summary']:
            snippets = [a['snippet'] for a in entry['articles'][:2]]
            entry['summary'] = snippets[0] if snippets else 'No updates found.'

    return digest


# --- HTML ---

STYLE_CARD = 'background: #fff; border-radius: 12px; padding: 20px; margin-bottom: 16px;'
STYLE_GREEN = STYLE_CARD + ' border-left: 4px solid #10b981;'


def format_html(mini_course, expert_digest):
    """Build the learning brief HTML email."""
    date_str = datetime.now().strftime('%A, %d %B %Y')

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 16px; color: #1a1a1a; background: #f0fdf4;">

<div style="{STYLE_CARD}">
  <h1 style="margin: 0 0 4px 0; font-size: 22px; color: #065f46;">AI Learning Brief</h1>
  <p style="margin: 0 0 2px 0; color: #666; font-size: 14px;">{date_str}</p>
  <p style="margin: 0; color: #10b981; font-size: 12px; font-weight: 600;">{mini_course.get('progress', '')}</p>
</div>
"""

    # Mini course — summary
    html += f'<div style="{STYLE_GREEN}">\n'
    html += f'  <div style="font-size: 12px; color: #10b981; font-weight: 600; margin-bottom: 4px;">{mini_course.get("week_label", "")}</div>\n'
    html += f'  <h2 style="margin: 0 0 12px 0; font-size: 18px; color: #065f46;">{mini_course["title"]}</h2>\n'

    # Render the summary (paragraphs + bullets)
    summary = mini_course.get('summary', '')
    if summary:
        for para in summary.split('\n'):
            para = para.strip()
            if not para:
                continue
            html += f'  <p style="font-size: 14px; line-height: 1.6; color: #333; margin: 0 0 10px 0;">{para}</p>\n'

    # Read more links
    if mini_course.get('articles'):
        html += '  <div style="margin-top: 14px; padding-top: 10px; border-top: 1px solid #d1fae5;">\n'
        html += '    <div style="font-size: 12px; color: #888; margin-bottom: 6px;">Read more:</div>\n'
        for a in mini_course['articles'][:3]:
            html += f'    <div style="margin-bottom: 4px;"><a href="{a["url"]}" style="font-size: 12px; color: #065f46;">{a["title"]}</a></div>\n'
        html += '  </div>\n'

    html += '</div>\n'

    # Expert digest — summaries
    html += f'<div style="{STYLE_GREEN}">\n'
    html += '  <h2 style="margin: 0 0 12px 0; font-size: 18px; color: #065f46;">Expert Digest</h2>\n'

    for expert in expert_digest:
        html += f'  <div style="margin-bottom: 14px;">\n'
        html += f'    <div style="font-size: 14px; font-weight: 600; color: #065f46; margin-bottom: 4px;">{expert["name"]}</div>\n'
        summary_text = expert.get('summary', '')
        if summary_text:
            html += f'    <div style="font-size: 14px; line-height: 1.5; color: #333;">{summary_text}</div>\n'
        # Read more link (top article only)
        if expert.get('articles'):
            a = expert['articles'][0]
            html += f'    <div style="margin-top: 4px;"><a href="{a["url"]}" style="font-size: 12px; color: #10b981;">Read more</a></div>\n'
        html += '  </div>\n'

    html += '</div>\n'

    html += f"""
<div style="text-align: center; padding: 16px; color: #999; font-size: 12px;">
  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; Enriquez OS
</div>
</body></html>"""

    return html


# --- Send ---

def send_email(html, subject, to_email):
    """Send via personal Gmail."""
    if not PERSONAL_TOKEN.exists():
        print("ERROR: Personal token not found. Run: python3 tools/auth_personal.py",
              file=sys.stderr)
        sys.exit(1)

    with open(PERSONAL_TOKEN, 'rb') as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    msg = MIMEMultipart('alternative')
    msg['to'] = to_email
    msg['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg['subject'] = subject
    msg.attach(MIMEText(html, 'html'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service = build('gmail', 'v1', credentials=creds)
    result = service.users().messages().send(
        userId='me', body={'raw': raw}
    ).execute()

    print(f"  Sent! Message ID: {result.get('id')}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description='AI Learning Brief')
    parser.add_argument('--send', action='store_true', help='Send email (default: generate data files only)')
    parser.add_argument('--dry-run', action='store_true', help='Preview only, no files written')
    parser.add_argument('--to', help='Override recipient email (requires --send)')
    args = parser.parse_args()

    to_email = args.to or TO_EMAIL_DEFAULT

    print("=== AI Learning Brief ===\n")

    print("--- Mini Course ---")
    mini_course = fetch_mini_course()

    print("\n--- Expert Digest ---")
    expert_digest = fetch_expert_digest()

    print("\n--- Formatting ---")
    html = format_html(mini_course, expert_digest)

    if args.dry_run:
        print(f"\n=== DRY RUN — preview only, no files written ===")
        print(f"  {mini_course.get('week_label', '')}")
        print(f"  Lesson: {mini_course['title']} ({len(mini_course['articles'])} articles)")
        for e in expert_digest:
            print(f"  {e['name']}: {len(e['articles'])} articles")
        return

    # Save data files (default behavior + --send)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    html_file = TMP_DIR / 'ai_learning_brief.html'
    html_file.write_text(html)
    print(f"  HTML saved to: {html_file}")

    if not args.send:
        print(f"\n=== Data files generated (no email sent) ===")
        print(f"  Use --send to also send the learning brief email")
        return

    print(f"\n--- Sending to {to_email} ---")
    subject = f"AI Learning Brief — {mini_course['title']}"
    send_email(html, subject, to_email)


if __name__ == '__main__':
    main()
