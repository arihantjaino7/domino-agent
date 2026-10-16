// Seed loader: (Site)-[:FEEDS]->(Site), tier-n material flow {component_id, cap_wk, used_wk}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Site {id: r.src})
MATCH (b:Site {id: r.dst})
CREATE (a)-[e:FEEDS]->(b)
SET e = r.props
RETURN count(e) AS created
