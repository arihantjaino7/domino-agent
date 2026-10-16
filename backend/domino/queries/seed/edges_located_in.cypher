// Seed loader: (Place)-[:LOCATED_IN]->(Region), site, port or plant -> region.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Place {id: r.src})
MATCH (b:Region {id: r.dst})
CREATE (a)-[e:LOCATED_IN]->(b)
SET e = r.props
RETURN count(e) AS created
