# Gemini-app route: ideas, research and script in Gemini, video in Claude

Ideas, research and the script run in the **Gemini chat app** (free with a Gemini plan) as three Gemini
**skills**. Narration runs in your terminal on the free Gemini TTS key. Claude is used only for the video.
Text moves between the Gemini app and the Short's folder by copy and paste; `facts.sh` saves what you copied and
checks it.

```
/Facts Ideas ──► pick a card ──► facts pick
/Facts Research ──► verify.md ──► facts save verify
/Facts Script ──► story JSON ──► facts save story (checker)
Terminal ──► facts narrate (free Gemini TTS + word timings)
Claude Code ──► /facts-shorts:video
```

## Files in this folder

| File | What it's for |
|---|---|
| `ideas-skill.md` | Description + instructions for the **Facts Ideas** skill |
| `research-skill.md` | Description + instructions for the **Facts Research** skill |
| `script-skill.md` | Description + instructions for the **Facts Script** skill |
| `quick-skill.md` | Description + instructions for the **Facts Quick Script** skill (topic → script, no research) |
| `facts.sh` (+ `facts_save.py`) | Terminal helper: copy skill text, ledger, save from clipboard, checker, narration |

Each `*-skill.md` starts with the **description** (line 2), then a `=== INSTRUCTIONS ===` line; everything
below that line is the **instructions**, including a worked example at the end (Research: a shortened real
verify.md; Script: a finished story JSON), so nothing needs attaching. `facts copy` copies the right part, so you
never select text by hand.

## One-time setup

### 1. Terminal shortcut

Add to `~/.zshrc` (use your real paths), then open a new terminal:

```bash
alias facts='"<plugin folder>/gemini/facts.sh"'
export FACTS_DIR="<content folder>"          # the folder holding channel.json and IDEAS.md
```

`facts` with no arguments prints its commands. Narration needs `GEMINI_FREE_KEY` (an AI Studio key from a
project **without billing**) in `~/.config/facts-shorts/.env` or `~/.config/football-stories/.env`.

### 2. Make the three skills

In the Gemini app: **Settings → Skills → Create manually**. For each skill:

| Name | Description box | Instructions box |
|---|---|---|
| `Facts Ideas` | `facts copy ideas description`, Cmd+V | `facts copy ideas`, Cmd+V |
| `Facts Research` | `facts copy research description`, Cmd+V | `facts copy research`, Cmd+V |
| `Facts Script` | `facts copy script description`, Cmd+V | `facts copy script`, Cmd+V |
| `Facts Quick Script` (optional) | `facts copy quick description`, Cmd+V | `facts copy quick`, Cmd+V |

Then save. Check the end of the Instructions box: Research ends with "...give the full verify.md again.",
Script ends with the example's closing `}`. If the text is cut short, the box has a size limit: tell Claude.

To use a skill: **new chat, type `/`, pick it**, then paste the input.

When the plugin's rules change (a new version of these files), edit each skill and paste the new description and
instructions. Skills don't update themselves.

**Still on Gems?** Open **gemini.google.com/gems/create** (your Gems: **gemini.google.com/gems/view**), use the
same name and instructions (Gems have no description box; nothing to attach). Google turns Gems
into skills automatically (from 13 Oct 2026; Gems end for personal accounts in Nov 2026).

## Making one Short

Use a **new chat** for each step of each Short. Long chats drift from the format.
Use the strongest model in the model picker for Research and Script.

### Step 1: idea (/Facts Ideas)

```bash
facts taken                       # prints the ledger and copies it
```

New chat, `/Facts Ideas`, paste, add a theme if you like ("something about money"), send.
You get 6 cards. Reply `pick 3`. It answers with two code blocks:

- a `facts pick ...` command: copy it and run it in the terminal (records the pick in IDEAS.md, makes the folder);
- a **research brief**: copy it for step 2.

### Step 2: research (/Facts Research)

New chat, `/Facts Research`, paste the brief, send. You get:

- one code block with the whole `verify.md`;
- a spine (hook → twist → payoff) and **Check these links**: open each link and confirm the sentence is on the
  page. This is the fact check that Claude used to do, so don't skip it. Wrong quote? Tell it
  ("claim 4's quote isn't on that page") and it gives a corrected file.

Then click the **copy** icon on the code block and run:

```bash
facts save verify <slug>
```

It saves the file, then checks it for the problems Gemini showed in testing: **links that don't exist** (it opens
every URL), homepages instead of articles, exam-prep / blog sources, LaTeX, and a changed layout. Any
`PROBLEM:` line means don't trust that version: start a **new** Facts Research chat, paste the brief plus the
PROBLEM lines, and save again. (Corrections in the same chat made Gemini invent sources in testing.)
`note: couldn't check` = the site blocks robots; open that link yourself.

For a hard topic you can turn on **Deep Research** in a normal Gemini chat with the same brief, then paste its
report into `/Facts Research` and ask: "turn this report into verify.md, judging every claim by your rules".

### Step 3: script (/Facts Script)

New chat, `/Facts Script`, send:

```
slug: <slug>
<paste verify.md here>
```

(`pbcopy < "$FACTS_DIR/<slug>/verify.md"` copies the saved file.)

You get a **beats table**. Edit as much as you like ("cut line 4", "funnier hook", "say it more simply").
When happy, say `final`. You get a JSON code block and a visual-ideas block.
Copy the **JSON** block, then:

```bash
facts save story <slug>
```

It saves `story.v1.json` and runs the checker. If you see `ERROR:` or `warn:` lines, copy them into the same
chat; it sends the fixed JSON; copy and `facts save story <slug>` again. Repeat until `OK`.
Keep the visual-ideas block for step 5.

### Step 4: narration (terminal, free)

```bash
facts narrate <slug>
```

Runs the checker, makes **one** take with `en-in-commercial-1` on the free key, times every word from the
pauses, and opens the audio. Listen for names and Hindi words said wrong. To fix one: change that line's
`tts` in the script chat (respell it, move the CAPS), save the story again, and narrate again.
Over 40 s? Ask the script chat to cut words.

### Step 5: video (Claude Code)

```
/facts-shorts:video <content folder>/<slug>/story.v1.json
Visual ideas: <paste the visual-ideas block>
```

The **content folder** is the folder `FACTS_DIR` points to (the one that holds `channel.json`, `IDEAS.md` and one
subfolder per Short). Run `echo $FACTS_DIR` to see it. Example, for the slug `sun-sneeze`:

```
/facts-shorts:video /Users/bansal.suraj/Documents/ai-learning/personal projects/facts-channel/sun-sneeze/story.v1.json
Visual ideas:
L1: <what's on screen>
L2: <what's on screen>
```

Run it in Claude Code from `personal projects`, because the plugin's skills are only found from that folder.

From here everything is the normal plugin: storyboard, photos (only after your yes), render, then
`/facts-shorts:metadata` and `/facts-shorts:revise`.

## Shortcut: topic → script without research (Facts Quick Script)

For a topic you know is well documented, skip Facts Research and let the model write from what it already knows.
It is faster, but the facts are **unchecked**: the skill only uses facts it is confident about, softens the rest,
and lists the 2-4 facts the video depends on for you to check on Wikipedia. Gemini invented sources in testing,
so don't skip that check. For anything surprising, disputed or about health, use the full route above.

1. **Topic.** Run `facts taken`, get cards from `/Facts Ideas`, say `pick N`, and run the `facts pick ...` line
   it gives you. (Have your own topic? Run `facts pick <slug> "<title>" "<category>" "<hook>"` yourself.)
2. **Script.** New chat → type `/` → pick **Facts Quick Script** → paste the research brief (or the idea card,
   or just a title and angle) → Enter.
3. **Edit** the beats table ("cut line 4", "funnier hook") until you like it, then type `final`. You get three
   code blocks: **JSON** (the script), **markdown** (the facts file) and **text** (visual ideas).
4. **Save the facts file:** copy the **markdown** block, then
   ```bash
   facts save quick <slug>
   ```
   It saves `verify.md` and prints **"Check these on Wikipedia before narrating"**.
5. **Check those facts** on Wikipedia (search the article, Cmd+F the year or name). One is wrong? Tell the same
   chat which, get the fixed script, type `final` again, and save both blocks again.
6. **Save the script:** copy the **JSON** block, then
   ```bash
   facts save story <slug>
   ```
   `ERROR:` / `warn:` lines? Paste them into the same chat, copy the new JSON, save again until `OK`.
7. **Then as usual:** `facts narrate <slug>`, listen, and in Claude Code
   `/facts-shorts:video <content folder>/<slug>/story.v1.json` with the visual-ideas block.

Order matters: save the facts file (step 4) before the script (step 6); the checker refuses a script with no
`verify.md` next to it.

## When something goes wrong

| What you see | Do this |
|---|---|
| `clipboard is empty` | Click the copy icon on the code block first (copying the whole reply also works) |
| `not valid JSON` | Paste the message into the script chat: "give me the full JSON again" |
| `doesn't look like verify.md` | You copied the spine or a link list; copy the code block |
| `PROBLEM: page does not exist` | Gemini invented that source. New Research chat; or ask Claude to research the claim |
| `already narrated` | Script changes now go through Claude: `/facts-shorts:revise` (makes v2) |
| The skill stops following the format | Start a new chat, pick the skill again, paste the input again |
| The wrong skill kicks in by itself | Pick the skill explicitly with `/` at the start of the chat |
| HTTP 429 in narrate | Free-tier limit; wait a few minutes and run it again |
| `already exists: pick another slug` | That slug is taken; use another one in `facts pick` |

You can mix routes any time: e.g. run `/facts-shorts:research <slug>` in Claude for a topic Gemini struggles
with; every step reads and writes the same files.
