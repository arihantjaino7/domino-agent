# Voiceover script (read this, or paste it into your voice tool)

About 340 words, 2 minutes 15 seconds at a calm speed. Leave a one-second pause between paragraphs. Short sentences on purpose.
Save the audio as `video/inputs/voiceover.wav` (or `.mp3` / `.m4a`). Keep it under 2 minutes 50 seconds.

---

**[1]**
In 2011, floods in Thailand stopped factories all over the world. Many companies did not know they depended on those factories. The problem was two tiers down.

**[2]**
This is DOMINO. It runs on FalkorDB, a graph database. Here is a made-up company, Kestrel Devices: suppliers, their suppliers, parts, factories, and one hundred seventeen customer orders.

**[3]**
An alert arrives: monsoon flooding in Ayutthaya, Thailand. Claude Code is the agent. It can only call DOMINO's fixed tools. It never writes database queries itself.

**[4]**
A tier-one view says: zero suppliers affected. But DOMINO follows the graph further up. A cell factory called VoltCell, inside the flood zone, feeds two of our battery suppliers. Thirty-eight orders are exposed. Thirteen will be late if nobody acts.

**[5]**
Next, the max-flow algorithm in FalkorDB measures the real capacity through the whole network. For one battery pack at one factory, the tier-one view promises nineteen hundred a week. The truth is seven hundred.

**[6]**
The cheapest backup supplier, AmpereOne, buys its cells from the same flooded factory. So DOMINO rejects it. Then it tests five plans, each on its own copy of the graph. Doing nothing leaves thirteen orders late. The chosen plan leaves one.

**[7]**
Nothing is bought without a human. I approve. DOMINO writes four purchase orders in one atomic step and checks the result: nine checks out of nine pass. Twelve orders are now protected on paper. The parts have not arrived yet, and the screen says so.

**[8]**
Every step shows the exact Cypher query it ran. And the final report is rejected if it states a number that no tool returned.

**[9]**
DOMINO also remembers. Lessons go into a memory graph with their date, and the next run recalls them.

**[10]**
We tested this on forty made-up disruptions. Doing nothing left three hundred eighty-three orders late. A tier-one plan left one hundred thirty. DOMINO left fifty-seven. An independent checker recomputed every case and found no mismatch.

**[11]**
DOMINO, built on FalkorDB, for Track One. When one link breaks, it finds the chain.
