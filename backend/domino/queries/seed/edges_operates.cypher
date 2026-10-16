// Seed loader: (Supplier)-[:OPERATES]->(Site), company -> its physical site.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Supplier {id: r.src})
MATCH (b:Site {id: r.dst})
CREATE (a)-[e:OPERATES]->(b)
SET e = r.props
RETURN count(e) AS created
