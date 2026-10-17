// Canvas: tier-n material flow between sites.
MATCH (a:Site)-[f:FEEDS]->(b:Site)
RETURN a.id AS src, b.id AS dst, f.component_id AS component, f.cap_wk AS cap_wk, f.used_wk AS used_wk
ORDER BY src, dst
