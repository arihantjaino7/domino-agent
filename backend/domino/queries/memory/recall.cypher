// Q-RECALL (memory graph): past incidents and lessons about the given entities, with the date learned.
MATCH (n:Entity) WHERE n.id IN $entity_ids
OPTIONAL MATCH (inc:Incident)-[inv:INVOLVED]->(n)
OPTIONAL MATCH (l:Lesson)-[ab:ABOUT]->(n)
RETURN n.id AS entity, n.name AS name, n.reliability AS reliability,
       collect(DISTINCT {id: inc.id, title: inc.title, learned_on: inc.learned_on}) AS incidents,
       collect(DISTINCT {text: l.text, learned_on: l.learned_on, incident_id: l.incident_id}) AS lessons
ORDER BY entity
