# Launch-ready posts — how to publish

Parked here (NOT in content/posts/) so nothing publishes by accident.

## Current contents

**The agency series (3 parts)** — split from the original single essay per Lucas's request, with his edits (spike sorting example, dog-in-the-sun line, "artifact", new opening) preserved, and a humanizing pass throughout:

1. `YYYY-MM-DD-independence-vs-agency.md` — "Independence Is Not Agency" (concept piece; ends teasing part 2)
2. `YYYY-MM-DD-ai-gave-me-independence-not-agency.md` — "AI Gave Me Independence. Agency Is Another Story." (refusals, the Fable 5 shutdown, hallucination stakes)
3. `YYYY-MM-DD-braille-has-never-mattered-more.md` — "Braille Has Never Mattered More" (elevator test, Ryles stat, multiline displays; the series' ending)

**Personal series opener:**

4. `YYYY-MM-DD-reflections-from-an-insomniac-ten-weeks-with-powell.md` — light copyedit only, voice untouched.

## To publish one

1. Rename: replace `YYYY-MM-DD` in the filename AND the `date:` line inside with the publish date.
2. Move it into `content/posts/`.
3. `python build/build.py`
4. Commit + push (the Get-ChildItem git one-liner). Live in ~2 minutes.
5. The build drops a LinkedIn-ready text file in `linkedin/`.

## Suggested cadence

Part 1 → one week later Part 2 → one week later Part 3. Each part = one newsletter send + LinkedIn/X/Bluesky announcement. The Powell piece slots nicely between or after the series. Publishing weekly parts beats one long essay: three visibility moments instead of one, and each piece is a 4–5 minute read.

## Notes

- Part 1 ends pointing at part 2, and each later part opens with a one-line recap — if you publish out of order, adjust those lines.
- The Anthropic Fable 5/Mythos 5 story in part 2 is fact-checked (June 9 launch, June 12 export-control shutdown, restored ~June 30) with Anthropic/Forbes/CNBC citations.
- The old single-essay version was replaced by this split. The original docx drafts on your machine are untouched.
- "The United States has finally broken me" deliberately not included — private for now.
