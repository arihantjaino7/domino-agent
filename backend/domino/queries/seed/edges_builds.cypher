// Seed loader: (Plant)-[:BUILDS]->(Product), {cap_day}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Plant {id: r.src})
MATCH (b:Product {id: r.dst})
CREATE (a)-[e:BUILDS]->(b)
SET e = r.props
RETURN count(e) AS created
