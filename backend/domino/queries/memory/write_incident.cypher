// Q-MEMORY-WRITE (runs on the `memory` graph): merge the incident and the entities it involved.
// learned_on is the calendar date the memory was written, so recall can say when it was learned.
// A name that is only the raw id (the entity is not in the current world) never replaces a real name.
MERGE (inc:Incident {id: $incident.id})
SET inc += $incident
WITH inc
UNWIND $entities AS e
MERGE (n:Entity {id: e.id})
SET n.kind = CASE WHEN e.name = e.id AND n.kind IS NOT NULL THEN n.kind ELSE e.kind END,
    n.name = CASE WHEN e.name = e.id AND n.name IS NOT NULL THEN n.name ELSE e.name END
MERGE (inc)-[inv:INVOLVED {role: e.role}]->(n)
RETURN count(inv) AS linked
