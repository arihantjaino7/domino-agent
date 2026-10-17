// Read-only JSON export for the independent evaluation oracle; no engine-derived fields.
MATCH (n)
RETURN labels(n) AS labels, properties(n) AS props
ORDER BY n.id
