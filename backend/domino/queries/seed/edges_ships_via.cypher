// Seed loader: (Site)-[:SHIPS_VIA]->(Port), logistics {days, cost_cents, mode}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Site {id: r.src})
MATCH (b:Port {id: r.dst})
CREATE (a)-[e:SHIPS_VIA]->(b)
SET e = r.props
RETURN count(e) AS created
