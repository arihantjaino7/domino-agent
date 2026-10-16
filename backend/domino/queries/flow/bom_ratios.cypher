// Units of each upstream component needed per unit of $component_id, along MADE_FROM (e.g. BAT-4S -> 4 cells).
MATCH p = (k:Component {id: $component_id})-[:MADE_FROM*1..4]->(c:Component)
RETURN c.id AS component, [r IN relationships(p) | r.qty] AS qtys
ORDER BY component
