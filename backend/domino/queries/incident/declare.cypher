// Q-DECLARE: one atomic write. Bumps world_version, creates the Incident once, then marks every
// affected site and links it with AFFECTS. The caller checks sites_affected == len($site_ids).
MATCH (m:Meta {id: 'META'})
SET m.world_version = m.world_version + 1
CREATE (inc:Incident {id: $incident_id, kind: $kind, title: $title, alert_text: $alert,
                      started_day: $day, expected_end_day: $end_day, severity: $factor, status: 'open'})
WITH inc, m
MATCH (s:Site) WHERE s.id IN $site_ids
SET s.status = 'disrupted', s.capacity_factor = $factor, s.disrupted_until = $end_day
CREATE (inc)-[a:AFFECTS {factor: $factor}]->(s)
RETURN inc.id AS incident, count(a) AS sites_affected, m.world_version AS world_version
