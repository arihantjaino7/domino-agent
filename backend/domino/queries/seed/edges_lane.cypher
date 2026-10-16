// Seed loader: (Port)-[:LANE]->(Port), logistics {days, eff_days, cost_cents, mode, cap_wk}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Port {id: r.src})
MATCH (b:Port {id: r.dst})
CREATE (a)-[e:LANE]->(b)
SET e = r.props
RETURN count(e) AS created
