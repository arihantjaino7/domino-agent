// All remembered lessons, newest first, with the date learned and the entities each is about (Memory tab).
MATCH (l:Lesson)
OPTIONAL MATCH (l)-[ab:ABOUT]->(n:Entity)
WITH l, collect(n.id) AS entities
RETURN l.id AS id, l.text AS text, l.learned_on AS learned_on, l.incident_id AS incident_id,
       l.evidence AS evidence, entities
ORDER BY learned_on DESC, id
