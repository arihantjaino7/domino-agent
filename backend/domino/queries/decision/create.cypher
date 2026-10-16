// Record a proposed plan as a Decision bound to its plan_hash and the world_version it was simulated on.
// MERGE keeps a re-proposal of the same decision id from creating a second node; the caller compares plan_hash.
MATCH (inc:Incident {id: $incident_id})
MERGE (d:Decision {id: $decision_id})
ON CREATE SET d.strategy = $strategy, d.status = 'proposed', d.plan_hash = $plan_hash,
              d.world_version = $world_version, d.budget_cents = $budget_cents, d.rationale = $rationale
MERGE (inc)-[r:RESOLVED_BY]->(d)
RETURN d.id AS decision, d.status AS status, d.plan_hash AS plan_hash
