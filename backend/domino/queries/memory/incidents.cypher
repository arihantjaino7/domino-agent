// All remembered incidents, newest first (Memory tab).
MATCH (inc:Incident)
OPTIONAL MATCH (inc)-[inv:INVOLVED]->(n:Entity)
RETURN inc.id AS id, inc.title AS title, inc.learned_on AS learned_on, inc.outcome AS outcome,
       collect(n.id) AS entities
ORDER BY learned_on DESC, id
