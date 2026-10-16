// Indexes on the graph (used to check that GRAPH.COPY carried them over).
CALL db.indexes() YIELD label, properties, types
RETURN label, properties, types
ORDER BY label
