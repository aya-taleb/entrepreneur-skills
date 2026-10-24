# entrepreneur-skills

Claude skills that help a founder find out if an idea is worth their time, before they build it.

## What do you want to do?

| I want to... | run this |
| --- | --- |
| tell Claude about my business once, so every skill writes for it | /founder-context |
| switch between my businesses | /founder-context |
| find out how big the market is, with sources | /market-research |
| know if I should go, narrow it down, or drop it | /market-research |
| know what to ask customers, and who to ask | /customer-discovery |
| turn my interview notes into evidence I can trust | /customer-discovery |
| test if people will pay before I build | /validate |
| read my test results and decide go, pivot or stop | /validate |
| make a draft sound like me, not a chatbot | /humanize |
| see who else does this and where the gap is | /competitors |

## Install

```
/plugin marketplace add aya-taleb/entrepreneur-skills
/plugin install entrepreneur-skills@entrepreneur-skills
```

This repo is also the hub for all 9 packs. After adding it once, install any of the others
the same way, for example `/plugin install mimic-skills@entrepreneur-skills`. In the Claude
app, add `aya-taleb/entrepreneur-skills` under Customize, Plugins, Add marketplace.

## Start here

Run `/founder-context` and tell it about your business in a few lines, or give it your
website. It asks a short batch of questions and saves one file that every other skill
reads. Then run `/market-research` on the idea.

Working files go in a `founder/` folder in your project, so each skill can pick up
where the last one stopped. Your business files live in `~/.founder/` (set `FOUNDER_HOME`
to use another folder). If an older version saved them inside `~/.claude`, `/founder-context`
offers to copy them over once, after you say yes.

## Good to know

- Nothing is made up. Every market number has a link or is marked as a guess, and
  missing numbers stay as `{{your number}}` for you to fill.
- You post and send everything yourself. No skill logs in, posts, messages people or
  scrapes sites for you.
- Interview quotes in your evidence log are your notes, word for word. Interest is not
  counted as demand.
- Pass and fail lines for a test are locked before it runs, so the result can't be
  bent to fit what you hoped.
- The humanize score comes from local pattern checks on your machine. It is not an AI
  detector, and it can't prove who wrote a text.

## The other repos

This repo is the hub. founder-context and humanize live here and are copied into the
others.

| repo | what it helps with |
| --- | --- |
| [entrepreneur-skills](https://github.com/aya-taleb/entrepreneur-skills) | Is this idea worth it? Market, interviews, demand tests. |
| [biz-ready-skills](https://github.com/aya-taleb/biz-ready-skills) | Turn the idea into a business that makes money: offer, brand, pricing, launch, funding. |
| [biz-boost-skills](https://github.com/aya-taleb/biz-boost-skills) | Get customers: prospect research, leads, cold email drafts, local outreach. |
| [mimic-skills](https://github.com/aya-taleb/mimic-skills) | Build a better version of a competitor, from research to launch. |
| [linkedin-boost-skills](https://github.com/aya-taleb/linkedin-boost-skills) | Grow on LinkedIn: posts, plans, comments, DMs you send yourself. |
| [instagram-boost-skills](https://github.com/aya-taleb/instagram-boost-skills) | Grow on Instagram: plans, carousels, stories, replies. |
| [multimedia-skills](https://github.com/aya-taleb/multimedia-skills) | Make the video and images: transcripts, promo videos, image and video generation. |
| [productivity-skills](https://github.com/aya-taleb/productivity-skills) | Run several ventures without dropping things: weekly review, tasks, people, decisions. |
| [video-boost-skills](https://github.com/aya-taleb/video-boost-skills) | Find what makes videos work now, get a dated checklist, and score your video before you post. |

## Credits

Made by Aya Taleb (github.com/aya-taleb). The humanize idea comes from Jake Schincariol's
li-human, ig-human and x-human skills, and the interview approach in customer-discovery
from wondelai's mom-test skill and Rob Fitzpatrick's book The Mom Test. Our tools and text
are written from scratch. See CREDITS.md. MIT.
