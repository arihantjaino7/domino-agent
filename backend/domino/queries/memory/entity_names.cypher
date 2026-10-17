// Runs on a WORLD graph: the display name and label of each id, so memory shows names, not raw ids.
// An id that is not in this world comes back with null name and kind.
UNWIND $ids AS id
OPTIONAL MATCH (n {id: id})
RETURN id, n.name AS name, CASE WHEN n IS NULL THEN null ELSE labels(n)[0] END AS kind
ORDER BY id
