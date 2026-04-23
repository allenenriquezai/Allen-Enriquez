#!/usr/bin/env python3
"""
Generate social media content for Allen's personal brand.

Usage:
    python3 tools/generate_content.py --type linkedin --topic "quote automation"
    python3 tools/generate_content.py --type linkedin --week
    python3 tools/generate_content.py --type reel --topic "speed to lead"
    python3 tools/generate_content.py --type youtube --topic "AI agents explained"
    python3 tools/generate_content.py --type fb-group-post --topic "VA automation tip"
    python3 tools/generate_content.py --type video-script --topic "speed to lead"
    python3 tools/generate_content.py --type email-newsletter --topic "why painters lose leads"
    python3 tools/generate_content.py --batch-day 1  (generates reel x2 + youtube for a campaign day)

Output: Content written to .tmp/content_drafts.json
"""

import argparse
import json
import os
import random
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT = os.path.join(ROOT, ".tmp", "content_drafts.json")

# Content pillars with templates
PILLARS = {
    "pain_point": {
        "label": "Pain Point",
        "hooks": [
            "The #1 reason painting companies lose leads has nothing to do with price.",
            "Most painting companies respond to leads in 24+ hours. By then, the job is gone.",
            "I talk to painting company owners every week. The same problem keeps coming up.",
            "Your best estimator is also your biggest bottleneck. Here's why that's killing growth.",
            "Painting companies don't have a marketing problem. They have a follow-up problem.",
        ],
        "body_template": (
            "{insight}\n\n"
            "I've seen this firsthand working with a painting company running a ${pipeline} pipeline.\n\n"
            "{real_example}\n\n"
            "{cta}"
        ),
    },
    "behind_the_scenes": {
        "label": "Behind the Scenes",
        "hooks": [
            "I just automated quoting for a painting company. Here's what happened.",
            "Last month I rebuilt how a painting company handles every new lead. The results surprised me.",
            "A painting company owner asked me to fix their quoting process. It turned into something bigger.",
            "I spent 3 weeks inside a painting company's sales process. Here's what I found.",
            "Before automation: 45 minutes per quote. After: under 5 minutes. Here's how.",
        ],
        "body_template": (
            "{insight}\n\n"
            "The numbers: {metric}.\n\n"
            "{real_example}\n\n"
            "{cta}"
        ),
    },
    "industry_insight": {
        "label": "Industry Insight",
        "hooks": [
            "I analyzed how painting companies in Charlotte handle leads. Most are leaving money on the table.",
            "The painting industry is 10 years behind on technology. That's actually good news.",
            "Here's what separates painting companies that grow from ones that stay stuck.",
            "3 things every $1M+ painting company does differently.",
            "The painting companies winning right now all have one thing in common.",
        ],
        "body_template": (
            "{insight}\n\n"
            "I've worked with companies managing {metric}.\n\n"
            "{real_example}\n\n"
            "{cta}"
        ),
    },
    "quick_tip": {
        "label": "Quick Tip",
        "hooks": [
            "One simple change that cut follow-up time in half for a painting company.",
            "Stop sending quotes as PDFs. Do this instead.",
            "The fastest way to lose a painting lead (and what to do about it).",
            "A 2-minute fix that stops leads from falling through the cracks.",
            "You don't need a CRM overhaul. You need this one workflow.",
        ],
        "body_template": (
            "{insight}\n\n"
            "When I implemented this for a client, {metric}.\n\n"
            "{real_example}\n\n"
            "{cta}"
        ),
    },
    "contrarian": {
        "label": "Contrarian",
        "hooks": [
            "Most painting companies don't need a CRM. Here's what they need instead.",
            "Hiring more estimators won't fix your quoting problem.",
            "The best painting companies I've seen don't compete on price. They compete on speed.",
            "Your website isn't losing you leads. Your response time is.",
            "Stop buying more leads. Start closing the ones you already have.",
        ],
        "body_template": (
            "{insight}\n\n"
            "Here's the proof: {metric}.\n\n"
            "{real_example}\n\n"
            "{cta}"
        ),
    },
}

METRICS = [
    "cut quote turnaround from 45 minutes to under 5",
    "$1.6M in active pipeline managed by one system",
    "83 active deals tracked automatically",
    "90% reduction in time spent on quotes",
    "follow-up emails sent same day instead of 3 days later",
    "zero leads lost to slow response since going live",
    "went from 2 quotes a day to 10+ without adding staff",
]

INSIGHTS = [
    "Speed wins. The first company to respond gets the job 78% of the time.",
    "Most owners are still doing quotes by hand. That means every quote costs them time they could spend selling.",
    "The bottleneck is never the work itself. It's the admin between the call and the quote.",
    "When you automate the boring stuff, your team focuses on what actually makes money.",
    "The companies growing fastest aren't spending more on ads. They're converting more of what they already get.",
]

EXAMPLES = [
    "One company I work with went from losing 3-4 leads a week to following up within hours. No new hires. Just better systems.",
    "A painting company in Brisbane was spending half their day on admin. We automated quoting, follow-ups, and lead tracking. Now the owner focuses on selling.",
    "I watched a company lose a $40K job because they took 3 days to send a quote. The homeowner went with someone faster.",
    "After automating the quote process, the estimator told me he finally had time to actually visit job sites instead of sitting at a desk.",
    "We built a system that pulls measurements, calculates pricing, and drafts the quote. The owner just reviews and hits send.",
]

CTAS = [
    "What's the biggest time sink in your painting business right now?",
    "If you could automate one part of your business tomorrow, what would it be?",
    "How long does it take you to send a quote after a new lead comes in?",
    "Have you ever lost a job just because you were too slow to respond?",
    "What would you do with an extra 2 hours every day?",
    "Is your quoting process helping you grow or holding you back?",
]

VIDEO_TEMPLATE = {
    "format": "15-30 second Loom",
    "structure": [
        {"section": "Hook (3-5 sec)", "say": "", "show": "Face to camera"},
        {"section": "Problem (5-10 sec)", "say": "", "show": "Screen share or face"},
        {"section": "Solution (10-15 sec)", "say": "", "show": "Demo/screenshot"},
        {"section": "CTA (3-5 sec)", "say": "", "show": "Face to camera"},
    ],
}

NEWSLETTER_TEMPLATE = {
    "format": "email newsletter",
    "structure": {
        "subject_line": "",
        "preview_text": "",
        "intro": "1-2 sentences, hook the reader",
        "main_section": "The insight — 3-4 short paragraphs",
        "example": "Real anonymized result",
        "cta": "Reply or click",
    },
}

# --- Hormozi-style templates for new content types ---

REEL_HOOKS = [
    "Stop doing {task} by hand.",
    "I saved {time} with one automation.",
    "Most businesses lose leads because of this.",
    "You don't need more leads. You need this.",
    "I built an AI assistant. Here's what it does.",
    "This one change saved me {time} every week.",
    "The #1 mistake small business owners make.",
    "AI won't replace you. But someone using AI will.",
    "Why are you still doing this manually?",
    "Free tool. {time} saved. Here's how.",
]

REEL_PROBLEMS = [
    "You spend hours on admin. Quoting. Follow-ups. Emails. It adds up.",
    "Every minute you spend on manual work is a minute you're not selling.",
    "You reply to a lead in 24 hours. They already hired someone else.",
    "You're good at your job. But the paperwork is slowing you down.",
    "Most businesses don't have a lead problem. They have a follow-up problem.",
]

REEL_SOLUTIONS = [
    "Step 1: Set up one automation. Step 2: Let it run. Step 3: Get your time back.",
    "AI can handle the follow-up. You handle the sale.",
    "One system. All your leads. Automatic follow-ups. Nothing falls through the cracks.",
    "Build it once. It works forever. No extra staff needed.",
    "Automate the boring stuff. Focus on what makes you money.",
]

REEL_CTAS = [
    "Follow for more AI tips.",
    "Save this for later.",
    "Comment 'HOW' and I'll show you.",
    "Drop a comment if you want the free guide.",
    "Share this with a business owner who needs it.",
    "Follow me for daily automation tips.",
]

YOUTUBE_HOOKS = [
    "I'm going to show you exactly how I {result}. Step by step.",
    "By the end of this video, you'll know how to {result}.",
    "Most people get this wrong. Here's what actually works.",
    "I went from {before} to {after}. Here's how.",
    "This one system changed how I run my entire business.",
]

YOUTUBE_STAKES = [
    "If you don't fix this, you'll keep losing time and money every single day.",
    "Every week you wait, your competitors get further ahead.",
    "Without this, you're working harder than you need to. And getting less.",
    "I used to spend hours on this. Now it takes minutes. The difference is what I'm about to show you.",
]

FB_POST_TEMPLATES = [
    "I just found out you can {action} with a free AI tool.\n\nIt takes 5 minutes and saves hours per week.\n\nHas anyone here tried this?",
    "Quick question for VAs here:\n\nWhat's the most repetitive task you do every day?\n\nI'm building a list of the top 10 tasks AI can handle.",
    "I helped a business owner automate their {process}.\n\nBefore: {pain}. After: {result}.\n\nWhat would you automate first?",
    "A lot of people ask me what AI agents are.\n\nSimple version: it's like a virtual assistant that works 24/7 and never forgets.\n\nWould a free guide on setting one up be helpful?",
]

TIME_SAVES = ["2 hours a day", "10 hours a week", "45 minutes per quote", "3 hours of follow-ups"]
TASKS = ["quoting", "follow-ups", "email replies", "lead tracking", "scheduling", "admin work"]
PROCESSES = ["quoting", "lead follow-up", "email outreach", "client onboarding"]
PAINS = ["45 minutes per quote", "leads falling through cracks", "no follow-up system", "manual everything"]
RESULTS = ["5 minutes per quote", "zero missed leads", "automatic follow-ups", "more time selling"]


def pick(lst):
    return random.choice(lst)


def generate_linkedin(topic=None, pillar_key=None):
    if pillar_key is None:
        pillar_key = random.choice(list(PILLARS.keys()))
    pillar = PILLARS[pillar_key]
    hook = pick(pillar["hooks"])
    body = pillar["body_template"].format(
        insight=pick(INSIGHTS),
        pipeline="1.6M",
        metric=pick(METRICS),
        real_example=pick(EXAMPLES),
        cta=pick(CTAS),
    )
    post = f"{hook}\n\n{body}"
    return {
        "type": "linkedin",
        "pillar": pillar["label"],
        "topic": topic or pillar["label"].lower(),
        "content": post,
        "word_count": len(post.split()),
        "status": "draft",
        "generated": datetime.now().isoformat(),
    }


def generate_week():
    pillar_keys = list(PILLARS.keys())
    random.shuffle(pillar_keys)
    posts = []
    today = datetime.now()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
    for i, key in enumerate(pillar_keys):
        post = generate_linkedin(pillar_key=key)
        post["scheduled_day"] = (monday + timedelta(days=i)).strftime("%A %b %d")
        posts.append(post)
    return posts


def generate_video_script(topic):
    script = json.loads(json.dumps(VIDEO_TEMPLATE))
    script["topic"] = topic
    script["structure"][0]["say"] = f"Quick tip for painting company owners about {topic}."
    script["structure"][1]["say"] = pick(INSIGHTS)
    script["structure"][2]["say"] = pick(EXAMPLES)
    script["structure"][3]["say"] = pick(CTAS)
    return {
        "type": "video-script",
        "topic": topic,
        "script": script,
        "status": "draft",
        "generated": datetime.now().isoformat(),
    }


def generate_newsletter(topic):
    template = json.loads(json.dumps(NEWSLETTER_TEMPLATE))
    template["subject_line"] = f"[Painting Automation] {topic.title()}"
    template["preview_text"] = pick(INSIGHTS)[:80]
    template["intro"] = pick(PILLARS[random.choice(list(PILLARS.keys()))]["hooks"])
    template["main_section"] = pick(INSIGHTS) + "\n\n" + pick(EXAMPLES)
    template["example"] = pick(METRICS)
    template["cta"] = pick(CTAS)
    return {
        "type": "email-newsletter",
        "topic": topic,
        "content": template,
        "status": "draft",
        "generated": datetime.now().isoformat(),
    }


def generate_reel(topic=None):
    hook = pick(REEL_HOOKS).format(task=pick(TASKS), time=pick(TIME_SAVES))
    problem = pick(REEL_PROBLEMS)
    solution = pick(REEL_SOLUTIONS)
    cta = pick(REEL_CTAS)

    script = (
        f"[HOOK] (0-3 sec)\n{hook}\n\n"
        f"[PROBLEM] (3-15 sec)\n{problem}\n\n"
        f"[SOLUTION] (15-45 sec)\n{solution}\n\n"
        f"[CTA] (45-60 sec)\n{cta}"
    )
    caption = f"{hook} {pick(REEL_CTAS)}"
    text_overlays = [hook.split(".")[0], pick(TIME_SAVES), cta.split(".")[0]]

    return {
        "type": "reel",
        "topic": topic or "automation tip",
        "platforms": ["instagram", "facebook", "tiktok", "youtube_shorts"],
        "script": script,
        "caption": caption,
        "text_overlays": text_overlays,
        "word_count": len(script.split()),
        "status": "draft",
        "generated": datetime.now().isoformat(),
    }


def generate_youtube(topic=None):
    hook = pick(YOUTUBE_HOOKS).format(
        result=pick(RESULTS), before=pick(PAINS), after=pick(RESULTS)
    )
    stakes = pick(YOUTUBE_STAKES)

    steps = random.sample(REEL_SOLUTIONS, min(3, len(REEL_SOLUTIONS)))
    framework = ""
    for i, step in enumerate(steps, 1):
        example = pick(EXAMPLES)
        framework += f"Step {i}: {step}\n  Example: {example}\n\n"

    proof = f"Here's the proof: {pick(METRICS)}.\n\n{pick(EXAMPLES)}"
    cta = "If this was helpful, subscribe. I post a new video every day showing you how to automate your business with AI."

    script = (
        f"[HOOK] (0-30 sec)\n{hook}\n\n"
        f"[STAKES] (30-90 sec)\n{stakes}\n\n"
        f"[FRAMEWORK] (90-360 sec)\n{framework}"
        f"[PROOF] (360-480 sec)\n{proof}\n\n"
        f"[CTA] (480-600 sec)\n{cta}"
    )

    title = topic or "How AI Can Run Your Business"
    return {
        "type": "youtube",
        "topic": topic or "AI automation",
        "title": f"{title[:57]}..." if len(title) > 60 else title,
        "description": f"Learn how to {topic or 'automate your business with AI'}. Simple steps. Real results.",
        "script": script,
        "word_count": len(script.split()),
        "chapters": [
            "0:00 — Hook",
            "0:30 — Why this matters",
            "1:30 — Step-by-step",
            "6:00 — Real results",
            "8:00 — What to watch next",
        ],
        "thumbnail_idea": f"Face + '{title[:20]}' + results number",
        "status": "draft",
        "generated": datetime.now().isoformat(),
    }


def generate_fb_post(topic=None):
    template = pick(FB_POST_TEMPLATES)
    content = template.format(
        action=f"automate {pick(TASKS)}",
        process=pick(PROCESSES),
        pain=pick(PAINS),
        result=pick(RESULTS),
    )
    return {
        "type": "fb-group-post",
        "topic": topic or "value post",
        "content": content,
        "word_count": len(content.split()),
        "status": "draft",
        "generated": datetime.now().isoformat(),
    }


def generate_batch_day(day_num):
    """Generate all content for one campaign day: 2 reels + 1 YouTube."""
    drafts = []
    reel1 = generate_reel(topic=f"Day {day_num} Reel #1")
    reel1["slot"] = 1
    drafts.append(reel1)

    reel2 = generate_reel(topic=f"Day {day_num} Reel #2")
    reel2["slot"] = 2
    drafts.append(reel2)

    yt = generate_youtube(topic=f"Day {day_num} YouTube")
    drafts.append(yt)

    return drafts


def main():
    parser = argparse.ArgumentParser(description="Generate personal brand content")
    parser.add_argument("--type", choices=[
        "linkedin", "video-script", "email-newsletter",
        "reel", "youtube", "fb-group-post",
    ])
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--week", action="store_true", help="Generate 5 LinkedIn posts for the week")
    parser.add_argument("--batch-day", type=int, default=None, help="Generate all content for a campaign day")
    args = parser.parse_args()

    if args.batch_day is not None:
        drafts = generate_batch_day(args.batch_day)
        print(f"Generated batch for Day {args.batch_day}: 2 reels + 1 YouTube")
        for d in drafts:
            print(f"  {d['type']}: {d.get('topic', '')} ({d.get('word_count', '?')} words)")
    elif args.type is None:
        parser.print_help()
        return
    elif args.type == "linkedin" and args.week:
        drafts = generate_week()
        print(f"Generated {len(drafts)} LinkedIn posts for the week:")
        for d in drafts:
            print(f"  {d['scheduled_day']} — {d['pillar']} ({d['word_count']} words)")
    elif args.type == "linkedin":
        drafts = [generate_linkedin(topic=args.topic)]
        print(f"Generated 1 LinkedIn post ({drafts[0]['word_count']} words)")
    elif args.type == "video-script":
        topic = args.topic or "automation for painters"
        drafts = [generate_video_script(topic)]
        print(f"Generated video script: {topic}")
    elif args.type == "email-newsletter":
        topic = args.topic or "painting automation"
        drafts = [generate_newsletter(topic)]
        print(f"Generated newsletter draft: {topic}")
    elif args.type == "reel":
        drafts = [generate_reel(topic=args.topic)]
        print(f"Generated reel script ({drafts[0]['word_count']} words)")
        print(f"  Platforms: {', '.join(drafts[0]['platforms'])}")
    elif args.type == "youtube":
        drafts = [generate_youtube(topic=args.topic)]
        print(f"Generated YouTube script: {drafts[0]['title']} ({drafts[0]['word_count']} words)")
    elif args.type == "fb-group-post":
        drafts = [generate_fb_post(topic=args.topic)]
        print(f"Generated FB group post ({drafts[0]['word_count']} words)")
    else:
        drafts = []

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(drafts, f, indent=2)
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
