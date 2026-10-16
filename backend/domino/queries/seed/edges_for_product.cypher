// Seed loader: (Order)-[:FOR_PRODUCT]->(Product), demand.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Order {id: r.src})
MATCH (b:Product {id: r.dst})
CREATE (a)-[e:FOR_PRODUCT]->(b)
SET e = r.props
RETURN count(e) AS created
