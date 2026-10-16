// What a site feeds one tier down, e.g. S-VOLT-AYU -> its tier-1 pack lines.
MATCH (s:Site {id: $site_id})-[f:FEEDS]->(t:Site)
RETURN t.id AS target, t.tier AS tier, f.component_id AS component, f.cap_wk AS cap_wk, f.used_wk AS used_wk
ORDER BY target
