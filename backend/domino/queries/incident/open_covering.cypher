// Open incidents that already affect any of these sites, with the sites each one covers.
// Used to make declare_incident idempotent: the same disruption is recorded once.
MATCH (i:Incident {status: 'open'})-[a:AFFECTS]->(s:Site)
WHERE s.id IN $site_ids
RETURN i.id AS incident, i.title AS title, i.expected_end_day AS end_day, collect(s.id) AS sites
ORDER BY incident
