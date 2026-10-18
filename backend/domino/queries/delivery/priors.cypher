// Seeded reliability of the company that operates each site (the prior that delivery facts update).
MATCH (s:Site)
WHERE size($site_ids) = 0 OR s.id IN $site_ids
OPTIONAL MATCH (sup:Supplier)-[op:OPERATES]->(s)
RETURN s.id AS site, s.name AS name, sup.reliability AS reliability
ORDER BY site
