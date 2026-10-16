// Health of candidate source sites and the reliability of the company that operates them.
MATCH (s:Site) WHERE s.id IN $site_ids
OPTIONAL MATCH (sup:Supplier)-[op:OPERATES]->(s)
RETURN s.id AS site, s.capacity_factor AS factor, s.status AS status, sup.reliability AS reliability
ORDER BY site
