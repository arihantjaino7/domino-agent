// Q-XRAY-PATHS: the evidence paths below each scanned site: variable-depth FEEDS chains (*0..4 includes the
// site itself when it is tier-1) to a tier-1 site and on to the plant it supplies, active (SUPPLIES) or backup
// (CAN_SUPPLY). One row per (chain, contract).
MATCH (s:Site) WHERE s.id IN $site_ids
MATCH chain = (s)-[:FEEDS*0..4]->(t1:Site)-[e:SUPPLIES|CAN_SUPPLY]->(pl:Plant)
RETURN s.id AS origin, [n IN nodes(chain) | n.id] AS path, t1.id AS tier1, pl.id AS plant,
       e.component_id AS component, type(e) AS contract
ORDER BY origin, contract DESC, tier1, plant, component
