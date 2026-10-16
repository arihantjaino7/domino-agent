// Q-MEMORY-WRITE (runs on the `memory` graph): merge the incident and the entities it involved.
// learned_on is the calendar date the memory was written, so recall can say when it was learned.
MERGE (inc:Incident {id: $incident.id})
SET inc += $incident
WITH inc
UNWIND $entities AS e
MERGE (n:Entity {id: e.id})
SET n.kind = e.kind, n.name = e.name
MERGE (inc)-[inv:INVOLVED {role: e.role}]->(n)
RETURN count(inv) AS linked
