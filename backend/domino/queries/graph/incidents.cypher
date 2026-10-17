// Incidents in this world with their footprint.
MATCH (i:Incident)
OPTIONAL MATCH (i)-[a:AFFECTS]->(s:Site)
RETURN i.id AS id, i.title AS title, i.kind AS kind, i.status AS status, i.started_day AS started_day,
       i.expected_end_day AS expected_end_day, collect(s.id) AS sites
ORDER BY id
