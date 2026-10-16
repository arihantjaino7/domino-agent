// Seed loader: (Region)-[:IN_ZONE]->(HazardZone), region -> hazard zone.
// A row whose endpoint is missing is dropped silently by MATCH, so the loader compares `created` with the batch size.
UNWIND $rows AS r
MATCH (a:Region {id: r.src})
MATCH (b:HazardZone {id: r.dst})
CREATE (a)-[e:IN_ZONE]->(b)
SET e = r.props
RETURN count(e) AS created
