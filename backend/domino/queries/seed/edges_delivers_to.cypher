// Seed loader: (Port)-[:DELIVERS_TO]->(Plant), logistics {days, cost_cents, mode}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Port {id: r.src})
MATCH (b:Plant {id: r.dst})
CREATE (a)-[e:DELIVERS_TO]->(b)
SET e = r.props
RETURN count(e) AS created
