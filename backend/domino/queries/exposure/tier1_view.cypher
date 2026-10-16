// Q-TIER1-VIEW: what a tier-1-only system sees. Affected sites that themselves supply a plant.
MATCH (inc:Incident {id: $incident_id})-[a:AFFECTS]->(s:Site)-[sup:SUPPLIES]->(pl:Plant)
RETURN count(DISTINCT s) AS directly_affected_tier1, collect(DISTINCT s.id) AS sites
