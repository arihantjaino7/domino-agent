// Approve a proposed decision. Only matches if the plan the human saw (plan_hash) is the one on record.
MATCH (d:Decision {id: $decision_id})
WHERE d.status = 'proposed' AND d.plan_hash = $plan_hash
SET d.status = 'approved', d.approved_by = $approved_by
RETURN d.id AS decision, d.status AS status
