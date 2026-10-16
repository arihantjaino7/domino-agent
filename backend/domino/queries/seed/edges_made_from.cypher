// Seed loader: (Component)-[:MADE_FROM]->(Component), multi-level BOM {qty}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Component {id: r.src})
MATCH (b:Component {id: r.dst})
CREATE (a)-[e:MADE_FROM]->(b)
SET e = r.props
RETURN count(e) AS created
