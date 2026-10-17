# Prompt for Codex: build the DOMINO demo video

How to use this file (for Arihant):

1. Put your audio at `video/inputs/voiceover.wav` (or `.mp3` / `.m4a`). The text to read is `video/voiceover-script.md`.
2. Optional: if you also screen-record a real Claude Code run, put it at `video/inputs/claude-code-terminal.mp4`.
3. Keep at least 10 GB free on C:. Docker's database crashed once when the disk was full.
4. Open Codex in `C:\dev\domino`, attach the file `Motion-Graphics-starter-kit.zip` (it is in Downloads), and paste everything inside the box below.

```text
You are a motion graphics designer and video editor. Build the 3-minute demo video for DOMINO, a hackathon project, in the repo C:\dev\domino. You will turn my voiceover into a finished video: screen footage of the real app, plus motion graphics timed to my exact words.

READ FIRST (in this order)
1. video/voiceover-script.md    the words in my audio
2. video/cues.md                which picture goes with which words (the storyboard)
3. video/facts.json             the ONLY numbers allowed on screen
4. docs/VIDEO.md                background on the video plan
5. The starter kit zip I attached: Motion-Graphics-starter-kit.zip. Unzip it into video/work/kit/ (a new folder). Its prompts.md is a reference for HyperFrames prompts. Its fonts/ and sfx/ folders are free to use (font licence is inside fonts/). Ignore its clip.mp4 and practice-screenshots/ (practice files).

INPUTS
- video/inputs/voiceover.(wav|mp3|m4a)  my voice. Keep it exactly as it is: do not re-record, re-pace, cut or denoise it. Only normalise the loudness (about -16 LUFS).
- video/inputs/claude-code-terminal.mp4  optional footage of the real Claude Code terminal. If it is missing, use the fallback described in cue 3.

WHAT TO MAKE
- One video: video/renders/domino-demo-1080p.mp4, 1920x1080, 30 fps, H.264 + AAC, at most 3:00 in total (my audio length + about 3 seconds of end card). Also video/renders/domino-demo.srt (captions) and a 5-line video/NOTES.md that says what you used and anything you could not do.
- Use HyperFrames, as in the kit: npx hyperframes (init, transcribe, check/lint, preview, render). Work in video/work/. If HyperFrames cannot be set up, stop and tell me exactly why. Do not switch to a different toolchain without asking.

SET UP (like the kit's PROMPT 01)
- First check free disk space on C:. If it is under 10 GB, stop and tell me.
- Check Node.js 22 or newer, FFmpeg and whisper-cpp. Install missing pieces only if no admin rights or password are needed; otherwise stop and give me the exact command. Run npx hyperframes doctor and ignore optional items (Docker, Kokoro, MusicGen).

STEP 1: TRANSCRIBE AND PLAN
- Run npx hyperframes transcribe on my audio to get word-level timestamps. Match every anchor phrase in video/cues.md to its timestamp. Print the list (phrase, start time, scene) before you build anything. If a phrase is missing or different in my audio, use the closest words and tell me.
- Cut the scenes on the rhythm of the words, like beats. Nothing should wait more than 1 second without movement.

STEP 2: CAPTURE THE APP FOOTAGE
The footage must be real screen recordings of the DOMINO war room, never redrawn. Record at 1920x1080 (use a 1920x1080 viewport) with Chrome via the Chrome DevTools screencast, or HyperFrames' own capture, whichever works. Do not edit any file in backend/ or frontend/.
- Start the database and app: make up, then make dev. The app is http://localhost:5173. (If make is not on your PATH, run the commands in the Makefile directly.)
- Replay mode plays a recorded run with no API key and no change to the graph. Use the real-model recording ("Claude Code over MCP", id monsoon-claude-code). If demo/replays/ has a newer real-model recording (agent "Claude Code over MCP" or "Claude API", latest recorded_utc), use that instead. Never use the "scripted" recording for scenes that say "Claude Code".
- For the healthy-world clip only: switch to Demo, press "Reset the world" (this resets the local world:live graph from world:pristine, which is safe), then switch back to Replay.
- Replay pauses by itself when the recorded plan needs approval. Press "Approve plan" yourself, after the approval card has been on screen for a full second. That click is part of the story.
- Clips to record (each 5 to 20 seconds, no mouse jitter, mouse hidden unless it clicks):
  A1  Overview, healthy world (after the reset), slow.
  A2  Overview during the replay: after the trace finishes, press the "Tier-1 view" button, hold 2 s, then press "DOMINO" so the path to VoltCell lights up.
  A3  "Supply chain" view: the card "... we can still get, per week" with the capacity bars (true vs tier-1 view).
  A4  "Supply chain" view: the node of AmpereOne Johor Bahru showing "no clean supply".
  A5  "AI agent" view: the card "The plans it tested" (five plans, late orders and cost).
  A6  The approval card ("Approve the rescue plan" / "Approve plan") and the click.
  A7  "Shipments" view after approval (the purchase orders).
  A8  "Overview" after approval: the headline "Plan approved ... protected (projected)".
  A9  "AI agent" view: click one finished step, then "Show a database query" so the Cypher drawer is open.
  A10 "AI agent" view: the panel "What DOMINO remembers", with the dated lesson visible.
- Add a small corner tag "Recorded run" on every one of these clips.
- When you finish capturing, stop make dev (kill its processes) and leave FalkorDB running.

STEP 3: BUILD THE VIDEO
- Style, kit-style but ours: take PROMPT 04 "Kinetic Type" from the kit as the base. Big words, black background, snappy moves, cuts on the beat. Use the fonts in the kit (Archivo Black for headlines and numbers, Inter for labels). Replace the lime accent with DOMINO's accent colour #c9637a (see frontend/src/index.css, --accent) and use #79b394 for good news (protected) and #d9566e for stopped or rejected. Show app clips inside rounded rectangles (radius 24) with a thin border on the black background, so the footage and the graphics look like one design.
- Follow video/cues.md scene by scene. Counters roll up on the exact word. Checklist ticks appear one at a time. Use only these kit sound effects, very quietly under my voice: tick (list items), counter (rolling numbers), chime (last card). No whooshes, no background music.
- Burn in word-level captions from the transcript: lower third inside the middle 80% of the width, never covering a clip's own text. Nothing but the title in the first 1.5 seconds.
- If you speed up any footage, show a small "2x" label.
- The hook, then the app: use kinetic type for scene 1 only and for the numbers; let the real screen footage carry the rest.

HONESTY RULES (this video is judged; wrong claims lose points)
- Show only the numbers in video/facts.json. Do not round, convert or invent numbers. Before rendering, write a small script that extracts every number that appears on screen and checks that it is in facts.json; fix anything else.
- Orders covered by purchase orders are "protected (projected)". Never write or say "fulfilled", "delivered", "optimal", "risk scan" or "normal tool". Use "Tier-1 view".
- Do not show or say anything that suggests the scripted demo is an AI thinking. Do not add logos, brands or photos you do not own. No stock photos: scene 1 is text only.
- Do not show the .env file, an API key, a personal browser tab, bookmarks or notifications. Hide the mouse cursor when it is not clicking.

QUALITY CHECKS BEFORE YOU SAY DONE
1. Total duration is 3:00 or less (ffprobe). My audio is untouched and in sync: every anchor phrase's visual starts within 0.3 seconds of the word.
2. Export a contact sheet (one frame per cue, plus the first and last frame) and look at it yourself: no overlapping text, nothing cropped on the sides, captions readable, clips sharp.
3. The facts check from the honesty rules passes.
4. Watch the render for the "2x" labels, the "Recorded run" tags and the end card with the GitHub link from facts.json.
5. Report: the final file path, its duration and size, the list of anchor phrases with their timestamps, and anything that did not work.

LIMITS
- Edit only files inside video/ (and append a short note to docs/CODEX_NOTES.md). Do not change backend/, frontend/, docs/PLAN.md, README.md or the Makefile. Do not push to GitHub. Do not run anything that costs money or calls a paid API. Do not delete Docker data, volumes or WSL disks.
- Do not commit video/renders, video/inputs or video/work (video/.gitignore already excludes them). If you commit, commit only source files, with a plain message and no AI attribution lines.
- If a step needs my decision (a missing clip, a font, a number), stop and ask me one short question instead of guessing.
```

## What stays with Claude (not Codex)

Codex builds the video. Claude's part is the real agent: the Claude Code run that is recorded in `demo/replays/monsoon-claude-code.json`, the data pack in `video/` (script, cue sheet, facts), and the app itself. If you make a better Claude Code run later, ask Claude to publish it as a new replay; the prompt above automatically prefers the newest real-model recording.
