// Seed loader: (Site)-[:CAN_SUPPLY]->(Plant), approved alternate {component_id, spare_wk, unit_price_cents, lead_days, transit_days, moq, qualified, ...}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Site {id: r.src})
MATCH (b:Plant {id: r.dst})
CREATE (a)-[e:CAN_SUPPLY]->(b)
SET e = r.props
RETURN count(e) AS created
