// Resolve incident entity ids against the graph (CLAUDE.md rule 3). Ids that match nothing come back with label null.
UNWIND $ids AS id
OPTIONAL MATCH (n:Place {id: id})
RETURN id, CASE WHEN n IS NULL THEN null ELSE labels(n) END AS labels
ORDER BY id
