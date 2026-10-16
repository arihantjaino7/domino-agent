// Direct FEEDS into the given sites (one tier up), with today's contract volume and cap.
MATCH (u:Site)-[f:FEEDS]->(s:Site)
WHERE s.id IN $site_ids
RETURN s.id AS site, u.id AS src, f.component_id AS component, f.cap_wk AS cap_wk, f.used_wk AS used_wk
ORDER BY site, src, component
