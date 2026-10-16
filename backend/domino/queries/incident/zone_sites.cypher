// Q-ZONE-SITES: expand a hazard zone to its regions and the sites located in them.
MATCH (z:HazardZone {id: $zone_id})<-[iz:IN_ZONE]-(r:Region)<-[li:LOCATED_IN]-(s:Site)
RETURN r.id AS region, collect(s.id) AS sites
ORDER BY region
