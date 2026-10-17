// A human rejected a proposed decision: record who and why, so the graph shows the decision was refused.
// Only a proposed decision can be rejected; an approved or executed one is left as it is.
MATCH (d:Decision {id: $decision_id})
WHERE d.status = 'proposed'
SET d.status = 'rejected', d.rejected_by = $rejected_by, d.feedback = $feedback
RETURN d.id AS decision, d.status AS status
