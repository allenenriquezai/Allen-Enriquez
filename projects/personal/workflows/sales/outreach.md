# Outreach SOP

Content brings people in. Outreach starts conversations. Both launch together.

## Channels (Priority Order)

| # | Channel | Primary Segments |
|---|---|---|
| 1 | Facebook DMs | VAs, Real Estate, MSMEs |
| 2 | Instagram DMs | VAs, Content Creators, Real Estate |
| 3 | LinkedIn | Recruitment Agencies, Allen's network |
| 4 | Phone calls | Warm leads, referrals |
| 5 | Email | Recruitment agencies, US businesses |

## Target Segments (Ranked)

| Segment | Score | Hook |
|---|---|---|
| Filipino VAs | 34/40 | "Here's how to become the VA clients can't replace." |
| Real Estate PH | 31/40 | "You lost 3 buyers today because you couldn't reply fast enough." |
| Recruitment Agencies | 31/40 | "Your competitor screened 200 resumes in 15 minutes." |
| US Service Biz | 30/40 | YouTube/SEO play -- let them find you |
| Filipino MSMEs | 27/40 | After case studies prove ROI |
| E-Commerce sellers | 27/40 | Target mid-to-large sellers only |

## Prospect Tiers

| Tier | Who | Approach |
|---|---|---|
| Tier 1 | Group admins, influencers, agency owners | Fully custom. Research first. One at a time. |
| Tier 2 | Active group members, question-askers | Template + personalization. Volume play. |
| Tier 3 | Allen's personal connections | No template. Real conversation. Ask for referrals. |

## Platform Limits

### Facebook DMs
| Action | Daily Limit |
|---|---|
| New threads (non-friends) | 10-15 |
| New threads (friends) | 30-40 |
| Friend requests | 10-15 |
| Group joins | 3-5 |

Spread across the day. Mix in normal activity. If Facebook warns, stop 48h.

### Instagram DMs
| Action | Daily Limit |
|---|---|
| DMs to non-followers | 10-15 |
| DMs to followers | 20-30 |
| Story replies | 30-50 |

Best tactic: reply to stories first. Opens natural DM thread.

### LinkedIn
| Action | Daily Limit |
|---|---|
| Connection requests | 20-25 |
| Messages to connections | 50+ |

### Email
Max 30 cold/day from personal Gmail. Start 5/day, increase weekly. Stop if bounce > 5%.

## Templates

### Facebook -- VAs (Tier 2)
> Hey [name]! Saw your post in [group] about [their problem].
> I had the same issue. I set up a simple AI tool that handles it automatically now. Took about 10 minutes.
> Want me to show you how?

### Facebook -- Real Estate (Tier 2)
> Hey [name]! Nice listing in [group].
> Quick question -- how do you handle it when 20+ people message you about the same property? I built a tool that auto-qualifies buyers and follows up for you.
> Want me to show you how it works?

### Instagram -- Cold DM (VA)
> Hey [name], loved your post about [topic].
> I help VAs automate repetitive tasks with AI -- emails, scheduling, data entry. Frees up hours.
> What tools are you using right now?

### LinkedIn -- Recruitment
> Hey [name], thanks for connecting.
> I noticed [agency name] focuses on [niche]. I built an AI system that screens and ranks candidates automatically -- hours to minutes.
> Would a quick demo be useful?

### Email -- Recruitment Agency
> Subject: Quick question about [agency name]'s screening process
> Hi [name], I help recruitment agencies in PH automate candidate screening. One agency cut screening from 3 hours to 15 minutes using AI. Worth a quick look? -- Allen

See full template library in outreach follow-up templates below.

## FB Group Outreach

- 2-3 value posts/week. Max 1 per group per week.
- Best days: Tue, Thu, Sat. Best time: 8-10 AM PH.
- Post types: quick wins, result shares, questions, education.
- End every post with a question.
- Never pitch in groups. No links. No selling.
- If someone asks "how?" -- reply briefly, then DM.
- DM sequence after engagement:
  1. "Hey [name], saw your comment. What's your situation?"
  2. Share a specific tip. No pitch.
  3. "I actually set this up for free -- want me to show you?"
- Be a member first. Comment on others' posts before posting your own.

### Filipino-Specific Notes
- Simple English. Pesos not dollars.
- "Sideline" and "extra income" resonate.
- Family-oriented framing ("more time with family").
- Don't position as guru. Position as fellow worker sharing what works.

## Tracking

Log every outreach to `projects/personal/.tmp/outreach_log.jsonl`:
```json
{
  "date": "YYYY-MM-DD",
  "channel": "FB DM",
  "segment": "VA",
  "tier": "Tier 2",
  "name": "Name",
  "platform": "Facebook",
  "group": "Group Name",
  "context": "What they posted about",
  "touch": 1,
  "status": "Drafted",
  "messages": {"touch_1": "...", "touch_2": "...", "touch_3": "..."}
}
```

Statuses: `Sent`, `Replied (warm)`, `Replied (not interested)`, `No reply`, `Cold`, `Warm -- follow up`, `Wants demo`, `Converted`

## Launch Plan

**Week 1:** Join 3-5 VA groups + 2-3 real estate groups. Post first clip. DM 10 VAs + 5 agents. IG: post reels, reply stories, DM 5. LinkedIn: connect 10 recruitment owners, message 5 friends.

**Week 2:** Volume up. FB: 10-15 VAs/day, 5-10 agents/day. IG: 10-15 story replies/day, 5-10 DMs. LinkedIn: 5 recruitment messages. Follow up Week 1 non-responders.

**Week 3-4:** Review conversions. Double down on winners. Start Touch 3 for Week 1. Train VA on Tier 2 templates when hired.

## Rules

1. Every day, outreach happens. No excuses.
2. Never pitch in the first message. Help first.
3. Personalize everything for Tier 1. Templates for Tier 2 only.
4. Respect the limits. Getting flagged kills the channel.
5. If ghosted after Touch 3, stop. Move on.
6. Track everything. If not in the log, it didn't happen.
7. Ask for referrals. Every warm conversation: "Who else might find this useful?"
8. Zero cost. No paid tools, no ads. All organic.
9. Content and outreach launch together.
