// Lessons (memory graph): one node per lesson, linked to the entities it is about.
UNWIND $lessons AS l
MERGE (les:Lesson {id: l.id})
SET les.text = l.text, les.incident_id = l.incident_id, les.learned_on = l.learned_on,
    les.evidence = l.evidence
WITH les, l
UNWIND l.entity_ids AS eid
MERGE (n:Entity {id: eid})
MERGE (les)-[a:ABOUT]->(n)
RETURN count(DISTINCT les) AS lessons, count(a) AS links
