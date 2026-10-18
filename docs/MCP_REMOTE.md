# Claude Code as DOMINO's agent, from any computer

The hosted DOMINO (for example https://domino-jiie.onrender.com) is also an MCP server at `/mcp/`. Claude Code on
any computer can connect to it with one command and act as the agent while the war room shows each step live.
Nothing from this repo is needed: the server serves the agent's playbook (`get_playbook` and the server
instructions) and one prompt per alert. A Claude subscription is enough; no Anthropic API key is used.

## Connect (once per computer)

```bash
claude mcp add --transport http --scope user domino https://domino-jiie.onrender.com/mcp/ --header "Authorization: Bearer YOUR_KEY"
```

- `--scope user` makes the server available in every folder on that computer.
- `YOUR_KEY` is the server's `MCP_API_KEY` (on Render: the service → **Environment**). The owner shares it with
  the people who should drive the public copy. If the server runs with `MCP_OPEN=true`, leave out `--header …`.
- Check it with `claude mcp list` (it should say `domino … Connected`).

## Run an alert

1. Open the site, choose mode **Claude Code** and press **Watch Claude Code**. The world resets and the page watches.
2. Run `claude` in any folder and send `/mcp__domino__monsoon` (or `/mcp__domino__panel_fire`,
   `/mcp__domino__non_event`, or `/mcp__domino__alert` with your own alert text). The prompt carries the alert and
   the playbook.
3. Claude Code calls DOMINO's tools; the war room shows each call and the Cypher behind it. When it says the plan is
   waiting, press **Approve** (or **Reject** with a reason) in the war room and tell Claude Code you decided. It then
   checks the status, verifies the execution, records lessons and files the report.

The war room's Claude Code mode shows the same steps with this site's address filled in and copy buttons.

## claude.ai or Claude Desktop

Settings → **Connectors** → **Add custom connector**, address `https://domino-jiie.onrender.com/mcp/?key=YOUR_KEY`
(custom connectors cannot send headers, so the key can go in the address). Then press **Watch Claude Code** in the
war room and ask: "Call get_playbook, then handle this alert: …". Not tested end to end; Claude Code is.

## Good to know

- **One shared world, one external run.** Two people driving it at the same time would mix their calls. Take turns.
- **Buying always needs the war room.** `submit_plan_for_approval` only proposes; the executor runs after a click on
  Approve, bound to the plan hash and the world version.
- The live copy is kept awake by a 5-minute health check. If it was asleep anyway, open the site first and wait for it to load before running `claude mcp list`.
- Tested on Oct 18 against the deployment image (`--memory=512m --cpus=0.1`): Claude Code in an empty folder, connected
  only by URL and header, ran `/mcp__domino__monsoon` through 18 tool calls, approval, 4 POs, 9 of 9 checks and an
  accepted report.
