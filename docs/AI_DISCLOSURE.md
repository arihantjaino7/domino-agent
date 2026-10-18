# AI assistance disclosure

DOMINO was conceived and directed by the author. The author originated the idea, directed the product and UI, tested the application and recorded demo screens. Claude Code and Codex helped turn those requirements and decisions into implementation and supporting material. The roles are set out below.

## Author's contribution

- **Idea and product direction:** the original DOMINO idea, the problem to solve, feature priorities and decisions about the intended behaviour came from the author.
- **UI concept and design direction:** the author supplied the UI thinking, design references and feedback, including the Rekora guide and iterative review of the war-room design. Claude Code implemented the interface from that direction.
- **Hands-on testing:** the author tested the application and demo flow, identified issues through use and directed revisions.
- **Demo recording and presentation decisions:** the author recorded demo screens and supplied their own voice for the initial video. The author also directed the use of real Claude Code replay evidence and visible corrections when narration and recorded results differed.
- **Final choices:** the author decides which changes, designs and demo version to use and is responsible for understanding and explaining the submitted system.

These author contributions were confirmed by the author on Oct 18, 2026.

## AI tools and their contribution

| Tool | Assistance |
|---|---|
| Claude Code (Anthropic) | helps in writing application code and automated tests from the project requirements; assisted with planning, implementation details, debugging, documentation, evaluation execution |
| Codex (OpenAI) | Wrote the independent evaluation harness and oracle, generated documentation, audited correctness and wording |

Claude Code also appears **inside the product** as the runtime agent over MCP. That is separate from its use as a development assistant: fixed deterministic engines compute the results, and purchase-order execution requires human approval.
