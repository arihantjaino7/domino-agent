// All remembered incidents, newest first (Memory tab). incident_id is the id it had in its world run;
// older memories, written before memory had its own ids, use the same id for both.
MATCH (inc:Incident)
OPTIONAL MATCH (inc)-[inv:INVOLVED]->(n:Entity)
RETURN inc.id AS id, coalesce(inc.incident_id, inc.id) AS incident_id, inc.title AS title,
       inc.learned_on AS learned_on, inc.outcome AS outcome, collect(n.id) AS entities
ORDER BY learned_on DESC, id DESC
