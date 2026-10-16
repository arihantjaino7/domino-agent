// Seed loader: (Site)-[:MAKES]->(Component), what a site produces {unit_price_cents}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Site {id: r.src})
MATCH (b:Component {id: r.dst})
CREATE (a)-[e:MAKES]->(b)
SET e = r.props
RETURN count(e) AS created
