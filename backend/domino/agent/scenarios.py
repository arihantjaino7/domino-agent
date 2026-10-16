"""Canned alerts for the demo scenarios (PLAN §12). The alert is data for the agent, not instructions."""

from domino.seed.motifs import MONSOON, PANEL_FIRE

SCENARIOS = {
    "monsoon": {"title": MONSOON["incident"]["title"], "alert": MONSOON["incident"]["alert_text"]},
    "panel_fire": {"title": PANEL_FIRE["incident"]["title"], "alert": PANEL_FIRE["incident"]["alert_text"]},
    # Not modelled in the graph: the agent must say "not in the graph", not "safe".
    "non_event": {"title": "Port strike in Antwerp",
                  "alert": "Dock workers' strike closes the Port of Antwerp for about a week."},
}
