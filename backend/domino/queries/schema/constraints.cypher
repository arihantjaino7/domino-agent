// Constraint status; GRAPH.CONSTRAINT CREATE is asynchronous, so schema.py polls this until OPERATIONAL.
CALL db.constraints() YIELD type, label, properties, status
RETURN type, label, properties, status
