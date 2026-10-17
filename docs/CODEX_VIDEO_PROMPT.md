# Prompt for Codex: build the DOMINO demo video

How to use this file (for Arihant):

1. Put your audio at `video/inputs/voiceover.wav` (or `.mp3` / `.m4a`). The words you read are in `video/voiceover-script.md`. It is fine if you stumbled and repeated lines: Codex cleans that up (see "FIX THE VOICEOVER").
2. Optional but best: if you also screen-record a real Claude Code run, put it at `video/inputs/claude-code-terminal.mp4`. If not, Codex builds the terminal scenes from the real recorded run.
3. Keep at least 10 GB free on C:. Docker's database crashed once when the disk was full.
4. Open Codex in `C:\dev\domino`, attach `Motion-Graphics-starter-kit.zip` (it is in Downloads), and paste everything inside the box below.
5. If you do not like your voice in the result: later put an AI voice at the same path and run the one command Codex documents in `video/NOTES.md`. Everything re-times itself.

```text
You are a motion graphics designer and video editor. Build the 3-minute demo video for DOMINO, a hackathon project, in the repo C:\dev\domino. You turn my voiceover into a finished video with three kinds of picture, all timed to my exact words:
  (1) real screen footage of the DOMINO war room (the app),
  (2) the Claude Code terminal, showing the real AI agent calling DOMINO's tools,
  (3) proper animated motion graphics: kinetic type, counters, diagrams, charts, transitions.

READ FIRST (in this order)
1. video/voiceover-script.md    the words in my audio
2. video/cues.md                which picture goes with which words (the storyboard)
3. video/facts.json             the ONLY numbers allowed on screen
4. docs/VIDEO.md                background on the video plan
5. The starter kit zip I attached: Motion-Graphics-starter-kit.zip. Unzip it into video/work/kit/ (a new folder). Its prompts.md is a reference for HyperFrames prompts. Its fonts/ and sfx/ folders are free to use (font licence is inside fonts/). Ignore its clip.mp4 and practice-screenshots/ (practice files).

INPUTS
- video/inputs/voiceover.(wav|mp3|m4a)  my voice, with possible mistakes (see FIX THE VOICEOVER). Never overwrite it; work on a copy in video/work/.
- video/inputs/claude-code-terminal.mp4  optional footage of the real Claude Code terminal (see CLAUDE CODE TERMINAL).

WHAT TO MAKE
- video/renders/domino-demo-1080p.mp4: 1920x1080, 30 fps, H.264 + AAC, at most 3:00 in total (the cleaned voice length + about 3 seconds of end card).
- video/renders/domino-demo.srt (captions) and video/NOTES.md (short: what you used, the ONE command that rebuilds everything from a new audio file, anything you could not do).
- Use HyperFrames, as in the kit: npx hyperframes (init, transcribe, check/lint, preview, render). Work in video/work/. If HyperFrames cannot be set up, stop and tell me exactly why. Do not switch toolchains without asking.
- Make the project voice-swappable: all scene start times are computed from a timings.json that is produced from the audio's transcript, never typed in by hand. If I replace the audio file and run the one command in NOTES.md, the whole video re-times and re-renders. Do not generate an AI voice now.

SET UP (like the kit's PROMPT 01)
- First check free disk space on C:. If it is under 10 GB, stop and tell me.
- Check Node.js 22 or newer, FFmpeg and whisper-cpp. Install missing pieces only if no admin rights or password are needed; otherwise stop and give me the exact command. Run npx hyperframes doctor and ignore optional items (Docker, Kokoro, MusicGen).

STEP 1: FIX THE VOICEOVER (I fumbled and repeated some lines)
- Copy my audio to video/work/voiceover-raw.wav (convert to 48 kHz mono or stereo WAV with ffmpeg). Transcribe it with word timestamps (npx hyperframes transcribe).
- Align the transcript against video/voiceover-script.md. Find: repeated sentences or phrases (I said a line again after a mistake), false starts, stumbles, filler sounds, long pauses and coughs/breaths that stand out.
- For every script sentence keep ONE take: normally the last complete, clean take (people repeat until it is right). Prefer an earlier take only if the last one is clearly worse (noise, cut-off, wrong words). Keep the final order exactly the order of the script.
- Cut with ffmpeg at points of low energy with 15 to 30 ms crossfades so there are no clicks. Do not change pitch or speed and do not add effects. Leave about 0.3 s between sentences and about 0.9 s between paragraphs; shorten any silence over 1.2 s. Light cleanup only: a gentle high-pass at 80 Hz, mild noise reduction if there is steady background noise, and loudness normalisation to about -16 LUFS.
- Re-transcribe the cleaned audio and compare it with the script. The captions and the timing come from the cleaned audio, not from the script. If I said different words from the script, keep my words and list the differences in your report. If a number I said differs from video/facts.json (13 vs 30, 38 vs 83, and so on), STOP and tell me; never silently change a number on screen.
- Save the cleaned audio as video/work/voiceover-clean.wav and write video/work/voice-edit-log.md: every cut (time in the raw file, what it removed, why) and every place where two takes were available and which one you chose. Never delete the raw file.
- Also report: raw length, cleaned length, how many fumbles/repeats you removed, and any sentence you could not repair (missing, too noisy, or only said wrongly).

STEP 2: TRANSCRIBE AND PLAN
- Using the cleaned audio, get word-level timestamps and match every anchor phrase in video/cues.md to its timestamp. Print the table (phrase, start time, scene) before building anything. If a phrase differs in my audio, use the closest words and tell me.
- Cut scenes on the rhythm of the words. Nothing may sit still for more than 1 second: there is always movement (a slow push-in, a counter, a type animation).

STEP 3: CAPTURE THE DOMINO WINDOW
The footage must be real screen recordings of the DOMINO war room, never redrawn. Record at 1920x1080 (a 1920x1080 viewport) with Chrome via the Chrome DevTools screencast, or HyperFrames' own capture, whichever works. Do not edit any file in backend/ or frontend/.
- Start the database and app: make up, then make dev. The app is http://localhost:5173. (If make is not on your PATH, run the commands in the Makefile directly.)
- Replay mode plays a recorded run with no API key and no change to the graph. Use the real-model recording ("Claude Code over MCP", id monsoon-claude-code). If demo/replays/ has a newer real-model recording (agent "Claude Code over MCP" or "Claude API", latest recorded_utc), use that instead. Never use the "scripted" recording for scenes that say "Claude Code".
- For the healthy-world clip only: switch to Demo, press "Reset the world" (this resets the local world:live graph from world:pristine, which is safe), then switch back to Replay.
- Replay pauses by itself when the recorded plan needs approval. Press "Approve plan" yourself, after the approval card has been on screen for a full second. That click is part of the story.
- Clips to record (each 5 to 25 seconds, mouse hidden unless it clicks):
  A0  "AI agent" view, press Play: the seven step nodes light up one after another as the tools run (about the first 20 seconds).
  A1  Overview, healthy world (after the reset), slow.
  A2  Overview during the replay: after the trace finishes, press "Tier-1 view", hold 2 s, then press "DOMINO" so the path to VoltCell lights up.
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

STEP 4: THE CLAUDE CODE TERMINAL
The video must show the Claude Code terminal, because it proves a real AI agent chooses the tools. Scenes T1, T2, T3 below appear in video/cues.md.
- If video/inputs/claude-code-terminal.mp4 exists: use that real footage, trimmed to the moments below, sped up where nothing happens (with a "2x" label).
- Otherwise build an animated terminal from the real recording demo/replays/monsoon-claude-code.json. Read its events: each tool.called has data.tool and data.args; each tool.result has data.result_ref, data.duration_ms, data.is_error and data.summary; every event has ts (use ts minus the first event's ts for the real timing). Show ONLY what is in that file; truncate long arguments with an ellipsis; never invent output.
  Design: a dark terminal window in JetBrains Mono (kit font), at least 28 px high text, tool names in the accent colour, one line per tool call that types in like a typewriter, then its result line (result_ref and milliseconds) fades in under it. Do not copy Anthropic's or Claude's logo or exact interface. Put this small label above the window: "CLAUDE CODE  |  REAL RUN  |  tool calls from the recording".
- T1 (cue 3): the first six to eight tool calls build up line by line (resolve_entities, declare_incident, trace_exposure, project_shortages, recall_history, compute_true_capacity ...), fast, next to the DOMINO clip A0. The real agent waited about a minute before its first call; cut that wait and show a "2x" label if you speed anything.
- T2 (cue 7): the call submit_plan_for_approval, then a blinking line "waiting for a human to approve in the DOMINO war room". Split screen with clip A6 (the approval card). When the click happens the terminal continues with get_decision_status, verify_execution, record_lessons.
- T3 (cue 8): the first submit_incident_report returns an ERROR line (use the first lines of data.summary: "report rejected; fix and resubmit" and the claim lines). Flash the line red, then the second submit_incident_report succeeds. This is real and it shows that numbers are checked. Keep the error text short enough to read.
- Layout: when the terminal and a DOMINO clip are on screen together, use a split screen (terminal left 40%, app right 60%, both in rounded rectangles) with a slow push-in on whichever side matters at that moment.

STEP 5: BUILD THE VIDEO (proper motion graphics, everywhere)
Style: take PROMPT 04 "Kinetic Type" from the kit as the base, adapted. Black background with a very faint animated dot grid, big words, snappy moves, cuts on the beat. Fonts from the kit: Archivo Black for headlines and numbers, Inter for labels, JetBrains Mono for the terminal. Accent colour #c9637a (DOMINO's, see frontend/src/index.css --accent) instead of the kit's lime; #79b394 for good news (protected); #d9566e for stopped or rejected; #d7a85a for "in danger". Show app clips and the terminal inside rounded rectangles (radius 24) with a thin border so footage and graphics look like one design.
Motion language (use the same easing family in the whole video, power3/power4.out, 0.25 to 0.6 s):
- Scene transitions of 6 to 10 frames, varied (push, wipe, zoom-through, mask reveal). Never the same transition three times in a row. Every scene has an entrance and an exit.
- A thin 7-step progress tracker (Detect, Trace, Impact, Options, Simulate, Approve, Verify; these are DOMINO's own steps) at the top that lights up as the story advances.
- Slow push-in (3 to 5 percent) on every screen clip, plus a punch-in on the part that matters (the number, the card, the button). Look at the frames to find where.
- Animated dependency diagram (scenes 4 and 6): draw it from the evidence paths in the "trace_exposure" result of demo/replays/monsoon-claude-code.json (names only from that file). Nodes appear tier by tier, lines draw themselves, a pulse travels from the flooded site to the factories and orders. The tier-1 view shows only the first column and the number 0; then the hidden second tier is revealed. AmpereOne is drawn attached to the same flooded factory and gets a REJECTED stamp.
- Animated counters (117, 38, 13, 1,900 to 700, 4, nine ticks, 383/130/71/57), bars that grow (plans: 13, 7, 3, 1, 1; results), a checklist that ticks one by one, a stamp that slams on REJECTED.
- Kinetic type for scene 1 (WHEN ONE LINK BREAKS) and for the key words of other scenes.
- Sound effects, quietly under my voice, from the kit only: tick (list items and checks), counter (rolling numbers), chime (last card). No whooshes, no background music.
- Burn in word-level captions from the cleaned transcript: lower third inside the middle 80% of the width, never covering a clip's own text. Nothing but the title in the first 1.5 seconds.
- Anything sped up gets a small "2x" label.

HONESTY RULES (this video is judged; wrong claims lose points)
- Show only the numbers in video/facts.json (and the real timings and names found in the recording). Do not round, convert or invent numbers. Before rendering, write a small script that extracts every number that appears on screen and checks that it is in facts.json or the recording; fix anything else.
- Orders covered by purchase orders are "protected (projected)". Never write or say "fulfilled", "delivered", "optimal", "risk scan" or "normal tool". Use "Tier-1 view".
- Never suggest the scripted demo is an AI thinking. The terminal scenes come only from the real Claude Code recording. No logos, brands or photos you do not own. No stock photos: scene 1 is text only.
- Do not show the .env file, an API key, a personal browser tab, bookmarks or notifications. Hide the mouse cursor when it is not clicking.

QUALITY CHECKS BEFORE YOU SAY DONE
1. Total duration is 3:00 or less (ffprobe). The audio you used is the cleaned voice, in sync: every anchor phrase's visual starts within 0.3 seconds of the word.
2. Listen-check the cleaned audio programmatically: re-transcribe it and confirm there are no repeated sentences left and no gap over 1.2 s.
3. Export a contact sheet (one frame per cue, plus the first and last frame) and look at it yourself: no overlapping text, nothing cropped at the sides, captions readable, terminal text readable, clips sharp.
4. The facts check from the honesty rules passes.
5. Check the "2x" labels, the "Recorded run" tags, the terminal label, and the end card with the GitHub link from facts.json.
6. Report: the final file path, its duration and size, the anchor-phrase table with timestamps, the voice edit summary (raw vs clean length, number of fumbles removed, sentences you could not repair), and anything that did not work.

LIMITS
- Edit only files inside video/ (and append a short note to docs/CODEX_NOTES.md). Do not change backend/, frontend/, docs/PLAN.md, README.md or the Makefile. Do not push to GitHub. Do not run anything that costs money or calls a paid API. Do not delete Docker data, volumes or WSL disks.
- Do not commit video/renders, video/inputs or video/work (video/.gitignore already excludes them). If you commit, commit only source files, with a plain message and no AI attribution lines.
- If a step needs my decision (a missing clip, a font, a number, a sentence I never said), stop and ask me one short question instead of guessing.
```

## What stays with Claude (not Codex)

Codex builds the video. Claude's part is the real agent: the Claude Code run recorded in `demo/replays/monsoon-claude-code.json`, the data pack in `video/` (script, cue sheet, facts), and the app itself. If you make a better Claude Code run later, ask Claude to publish it as a new replay; the prompt above automatically prefers the newest real-model recording.
