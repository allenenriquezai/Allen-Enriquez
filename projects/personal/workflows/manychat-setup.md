# ManyChat Setup — SOP

Allen follows this guide to set up ManyChat for inbound automation on Facebook and Instagram. When someone comments a keyword on a reel or carousel, ManyChat auto-sends them a DM. Zero manual effort after setup.

**Free tier covers everything needed:** comment-to-DM triggers, unlimited contacts, unlimited flows, FB + IG automation. No need to upgrade yet.

---

## Setup

### 1. Create Account
1. Go to manychat.com > "Get Started Free" > sign up with Facebook > choose Free plan

### 2. Connect Facebook Page
1. Settings > Channels > Facebook > Connect Facebook Page
2. Select your brand page. Grant all permissions.
3. You need a Facebook Page, not a personal profile.

### 3. Connect Instagram
1. Your IG must be a Business/Creator account linked to your FB Page
2. Settings > Channels > Instagram > Connect Instagram > Authorize
3. **Won't connect?** Check IG is Business/Creator (IG Settings > Account > Switch to Professional). Check IG is linked to FB Page (FB Page Settings > Instagram).

### 4. Create a Keyword Trigger
1. Automation > New Automation
2. Trigger: "Instagram Comment" or "Facebook Comment"
3. Set keyword (e.g., "AI"). Match type: "contains keyword" (catches "AI please" etc.)
4. Choose "Specific post" (start here) or "All posts" (once tested)
5. Add action: "Send Message" — paste DM copy from flows below
6. Replace [YouTube link] with your actual link
7. Optional: Add "Reply to Comment" action — set text to "Sent! Check your DMs." (social proof)
8. Optional: Add "User Input" block after message — store reply in Custom Field (e.g., "first_response")
9. Toggle ON. Test from a second account before going live.

Repeat for each keyword flow. Five total.

---

## Comment-Trigger Flows

Each flow maps to a content pillar. Post content with the keyword CTA. ManyChat handles the rest.

### Flow 1: "AI" — Automation Results
**Use on:** Reels/carousels showing before/after, metrics, proof
**DM:**
> Hey! You commented AI so here's what I promised.
>
> I built an AI system that runs my entire sales process. Quotes, follow-ups, emails — all automatic.
>
> Here's a free video showing the exact setup: [YouTube link]
>
> What do you do for work? I'll tell you what you can automate first.

### Flow 2: "VA" — VA Upskilling
**Use on:** Content about VAs using AI, upskilling, automation
**DM:**
> Hey! Thanks for commenting.
>
> AI is replacing basic VA work right now. But VAs who learn AI are charging 2-3x more.
>
> I made a free guide on the 5 AI tools every VA should know: [YouTube link]
>
> What VA tasks do you do the most? I'll show you which ones AI can handle.

### Flow 3: "AUTOMATE" — Business Owner Pain Points
**Use on:** Content about slow quotes, missed leads, admin overload
**DM:**
> Hey! You want to automate — good.
>
> Most business owners waste 2-3 hours a day on tasks AI can do in seconds. Emails, follow-ups, scheduling, quotes.
>
> I set this up for people for free. No catch. I just want to show you what's possible.
>
> What's the one task that eats most of your time? I'll tell you exactly how to automate it.

### Flow 4: "HOW" — Behind the Scenes
**Use on:** Screen recordings, live builds, system walkthroughs
**DM:**
> Hey! You asked how — here's the breakdown.
>
> I use Claude Code to build AI agents that do real work. Not chatbots. Actual systems that send emails, create quotes, follow up with clients.
>
> Here's the full tutorial: [YouTube link]
>
> Want me to walk you through setting up your first one? Takes 10 minutes.

### Flow 5: "FREE" — General Catch-All
**Use on:** Any content where Allen offers something free
**DM:**
> Here you go! As promised: [YouTube link or resource link]
>
> This shows you step by step how to set it up yourself. Zero cost.
>
> If you get stuck or want me to set it up for you, just reply here. Happy to help.

---

## CTA Templates

### Carousel Last Slide (pick one per post)

| Keyword | Slide text |
|---|---|
| AI | Want the full tutorial? Comment "AI" below. I'll send it to your DMs. Free. |
| VA | Are you a VA? Comment "VA" below. I'll send you 5 AI tools that save hours every day. |
| AUTOMATE | Want to automate this? Comment "AUTOMATE" below. I'll show you how. Free. |
| HOW | Want to see how I built this? Comment "HOW" below. Full breakdown in your DMs. |
| FREE | Want this for free? Comment "FREE" below. I'll send it straight to your DMs. |

### Reel Spoken CTA (last 5 seconds)

- "Comment AI and I'll send you the full tutorial."
- "Comment VA — I'll send you the tools."
- "Comment AUTOMATE — I'll show you how. Free."
- "Comment HOW and I'll DM you the breakdown."
- "Comment FREE and I'll send it to your DMs."

Always add a text overlay of the keyword on the last frame too.

---

## Free Tier Limits

| Limit | Impact |
|---|---|
| 10 custom fields | Use wisely: first_response, segment, lead_status |
| No sequences | Can't auto-send follow-up after 24h. All follow-up is manual. |
| No SMS/email | DMs only |
| No Zapier/API | Can't connect to Sheets or CRM |
| No A/B testing | Test manually by switching copy weekly |

**Upgrade to Pro ($15/month) when:** You want drip sequences, need more custom fields, want CRM integration, or volume makes manual follow-up impossible. Don't upgrade until 100+ contacts are flowing through.

---

## Daily Workflow

1. Post content with keyword CTA (reel or carousel)
2. ManyChat auto-DMs everyone who comments the keyword
3. Check ManyChat inbox once a day (evening)
4. Reply to anyone who responded to the auto-DM
5. Log warm leads in CRM (use outreach.md tracking format)

**Time cost:** 5 min setup per post. 10-15 min daily checking replies.

---

## Rules

1. **One keyword per post.** Don't confuse people with multiple CTAs.
2. **Test every flow before going live.** Comment from a second account.
3. **Keep DM copy under 80 words.** People don't read long DMs.
4. **Always ask a question in the DM.** Replies = warm leads.
5. **Check inbox daily.** Auto-DM opens the door. You close it.
6. **Don't over-automate.** The real conversation is manual and personal.
7. **Update links when you publish new content.** Stale links = dead leads.
8. **Say "free" early.** Filipino market is price-sensitive.
9. **Track results.** Which keyword gets the most comments? Double down on winners.
