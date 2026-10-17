// Read-only export of raw relationships, including parallel edges and their properties.
MATCH (a)-[e]->(b)
RETURN a.id AS src, b.id AS dst, type(e) AS type, properties(e) AS props
ORDER BY src, dst, type
