// Seed loader: (Order)-[:FULFILLED_AT]->(Plant), demand.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Order {id: r.src})
MATCH (b:Plant {id: r.dst})
CREATE (a)-[e:FULFILLED_AT]->(b)
SET e = r.props
RETURN count(e) AS created
