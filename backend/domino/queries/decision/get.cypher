// Decision state plus the current world_version, for the executor's pre-write checks.
// feedback is set only when a human rejected the decision.
MATCH (m:Meta {id: 'META'})
OPTIONAL MATCH (d:Decision {id: $decision_id})
RETURN d.id AS decision, d.status AS status, d.plan_hash AS plan_hash, d.world_version AS decision_world_version,
       d.budget_cents AS budget_cents, d.feedback AS feedback, m.world_version AS world_version
