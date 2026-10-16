// Seed loader: (Site)-[:SUPPLIES]->(Plant), active contract {component_id, used_wk, unit_price_cents, transit_days}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Site {id: r.src})
MATCH (b:Plant {id: r.dst})
CREATE (a)-[e:SUPPLIES]->(b)
SET e = r.props
RETURN count(e) AS created
