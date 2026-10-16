// Expand a region to the sites located in it.
MATCH (r:Region {id: $region_id})<-[li:LOCATED_IN]-(s:Site)
RETURN s.id AS site
ORDER BY site
