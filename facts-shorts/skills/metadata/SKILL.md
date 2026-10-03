---
name: metadata
description: Draft the YouTube title, description, hashtags, pinned comment and an India posting slot for a finished facts-channel Short (Hinglish + English), with photo credits and "Narration voice is AI-generated.", written to metadata.md. Works without any channel history (a new channel); switch to yt-insights:metadata once the channel has uploads to learn from. Use when the user says "title for the facts short", "description and hashtags", "metadata for this short", or invokes /facts-shorts:metadata.
---

# Metadata

Finished Short in, `metadata.md` out (paste-ready). Upload stays manual.

## Paths

| What | Where |
|---|---|
| Story | `<root>/<slug>/story.v<N>.json` (latest), `verify.md`, `src/sources.json`, `<slug>_v<N>.mp4` |
| Channel | `<root>/channel.json` (name, promise, timezone) |
| Output | `<slug>/metadata.md` |
| Cost | `${CLAUDE_PLUGIN_ROOT}/scripts/cost.py` |

## Procedure

1. **Read** the story lines, verify.md (compact table), `src/sources.json`, channel.json. If the channel has uploads and `yt-insights` data exists for it, say that `/yt-insights:metadata` can now use its top videos as the style reference.
2. **Titles (3 options).** Under 60 characters, the hook question or its twist, Hinglish or English (one each, plus one mixed), no clickbait the video doesn't pay off, no all-caps sentences, at most one emoji. Lead with the familiar object.
3. **Description.**
   - Line 1: the hook in Hinglish (shows in the feed). Line 2: one-sentence English summary for search.
   - 2–3 short lines with the story in your own words (no stitched quotes).
   - "Sources:" 2–3 short source names from verify.md (publisher + page title; no long URL lists).
   - "Photos:" one credit per image from `src/sources.json` (`<title>, <licence>, via Wikimedia Commons`; CC BY/BY-SA files need author + licence).
   - `Narration voice is AI-generated.` (always, exact text).
4. **Hashtags.** 3–5 in the description's last line: `#Shorts`, one topic tag, one Hinglish/India tag (e.g. `#HindiFacts`, `#FactsInHindi`), one English (`#DidYouKnow`, `#History`). Plus 8–12 comma-separated tags for the Studio tags field (topic words, Hinglish spellings).
5. **Pinned comment.** A question that invites answers ("Aapke ghar mein phone uthake kya bolte the? 👇") or a related teaser; not "like and subscribe".
6. **Posting slot.** Suggest an IST slot as a starting heuristic, not a fact: evenings (7–9 pm IST) on weekdays or late morning on weekends, and say it should be replaced by the channel's own Analytics after ~10 uploads.
7. **Write `metadata.md`** with sections Titles / Description (in a code block, paste-ready) / Hashtags / Tags / Pinned comment / Slot / Checklist (made for kids: No; altered or synthetic content: answer per YouTube's prompt, the voice is AI; category: Education).
8. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "metadata" --slug <slug>`. Show the titles, the description block and the cost lines.
9. **Ledger.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ideas.py set <slug> --status made --note "<slug>_v<N>.mp4"`.

## Hard rules

- Every fact in the description is VERIFIED in verify.md. No new claims.
- "Narration voice is AI-generated." is always in the description.
- Photo credits match `src/sources.json`. Nothing is uploaded or published by this skill.
