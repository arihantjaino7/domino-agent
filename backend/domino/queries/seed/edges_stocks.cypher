// Seed loader: (Plant)-[:STOCKS]->(Component), inventory {on_hand, safety}.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Plant {id: r.src})
MATCH (b:Component {id: r.dst})
CREATE (a)-[e:STOCKS]->(b)
SET e = r.props
RETURN count(e) AS created
