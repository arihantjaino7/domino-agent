// Inject menu: hazard zones and regions with how many sites each would hit.
MATCH (r:Region)
OPTIONAL MATCH (r)-[iz:IN_ZONE]->(z:HazardZone)
OPTIONAL MATCH (s:Site)-[li:LOCATED_IN]->(r)
RETURN r.id AS region, r.name AS region_name, r.country AS country, z.id AS zone, z.name AS zone_name,
       z.hazard AS hazard, count(s) AS sites
ORDER BY zone, region
