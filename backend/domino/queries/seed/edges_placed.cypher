// Seed loader: (Customer)-[:PLACED]->(Order), demand.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Customer {id: r.src})
MATCH (b:Order {id: r.dst})
CREATE (a)-[e:PLACED]->(b)
SET e = r.props
RETURN count(e) AS created
