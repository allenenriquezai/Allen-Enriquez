# Personal — Allen Enriquez

Covers two areas:

**Personal life** — automations for self, friends, and family. Eliminate manual, low-effort tasks. Outputs go to tools Allen already uses (WhatsApp, Google Sheets, etc.).

**Personal brand** — AI automation educator + service provider. Pre-revenue. Content-led growth on YouTube, then convert viewers to clients.

## Strategy
Build in public. Show how Allen automates his real job (EPS) using AI. Teach people how to do it for free. Attract professionals who either learn and DIY, or realize they'd rather pay someone. Content is the top of funnel. Outreach is the accelerator.

## Offer
- Free: YouTube content teaching AI automation step by step
- Paid: "We'll build it for you" — done-for-you automation setup
- No fixed pricing yet. Start free, prove value, then price based on scope.

## ICP (Primary — Philippines)
- Virtual assistants wanting to upskill with AI
- Small business owners (any industry) wanting to automate
- Professionals: realtors, architects, service businesses
- People already somewhat tech-aware but not building AI systems yet

## ICP (Secondary — US cold outreach)
- Service businesses (painting, cleaning, renovation)
- Owner-operators overwhelmed by admin
- Basic or outdated tech stack

## Channels
- **Content:** YouTube (long-form), Reels (IG/FB/TikTok/YT Shorts)
- **Outreach:** LinkedIn, Facebook messaging, Instagram DMs
- **Ads:** Facebook ads (later, once organic content is validated)

## Content Approach
One small automation per video. Never show the full OS at once. Make each piece digestible — "here's how I automated follow-up emails" not "here's my entire AI system." Build the full picture over time as viewers follow along. Hook them with simple wins first.

## Department Structure

Full org chart: `projects/personal/org/departments.md`

5 departments: Intelligence Unit, Content Production, Sales, Delivery + Brand Manager (universal QA gate above all).

**Key locations:**
- Intelligence docs: `reference/intel/` (7 living docs — all agents read these before work)
- Delivery client files: `.tmp/clients/{client-name}/`
- Agent prompts: `agents/`

**Brand Manager** is the universal QA gate with 3 tiers (auto-approve, spot-check, full review). All output passes through it.

**Rule:** All content and outreach agents MUST read `reference/intel/` before planning or writing. Intel feeds everything.

## Environment
Credentials: `projects/personal/.env`
Workflows: `projects/personal/workflows/`
Temp files: `projects/personal/.tmp/`
