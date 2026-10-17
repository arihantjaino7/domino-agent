// Canvas: every site with its tier, health, operator and region.
MATCH (s:Site)
OPTIONAL MATCH (sup:Supplier)-[op:OPERATES]->(s)
OPTIONAL MATCH (s)-[li:LOCATED_IN]->(r:Region)
RETURN s.id AS id, s.name AS name, s.tier AS tier, s.kind AS kind, s.status AS status,
       s.capacity_factor AS factor, s.disrupted_until AS disrupted_until, s.capacity_wk AS capacity_wk,
       s.unit AS unit, sup.name AS operator, r.id AS region, r.name AS region_name, r.country AS country
ORDER BY id
