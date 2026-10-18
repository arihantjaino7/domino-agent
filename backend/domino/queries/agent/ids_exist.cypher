// Resolve tool arguments against the graph before anything runs.
UNWIND $ids AS id
OPTIONAL MATCH (n {id: id})
RETURN id, CASE WHEN n IS NULL THEN null ELSE labels(n) END AS labels
ORDER BY id
