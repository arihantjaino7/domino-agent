// Lessons already stored for one memory incident (memory graph): how many, and their texts, so a new
// call adds lessons with the next ids and skips a lesson that is already there.
MATCH (l:Lesson {incident_id: $incident_id})
RETURN count(l) AS n, collect(l.text) AS texts
