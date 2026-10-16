// Q-SHARED: affected upstream sites that feed two or more tier-1 sites (active or alternate).
// This is the proof that "independent" backups share a hidden dependency.
MATCH (inc:Incident {id: $incident_id})-[a:AFFECTS]->(d:Site)
MATCH (d)-[f:FEEDS*1..4]->(t1:Site)-[e:SUPPLIES|CAN_SUPPLY]->(pl:Plant)
WITH d, collect(DISTINCT t1.id) AS dependents
WHERE size(dependents) >= 2
MATCH (sup:Supplier)-[op:OPERATES]->(d)
RETURN d.id AS shared_upstream, sup.name AS operator, dependents, size(dependents) AS fan_out
ORDER BY shared_upstream
