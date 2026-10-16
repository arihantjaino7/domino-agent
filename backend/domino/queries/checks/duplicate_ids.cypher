// Any id carried by more than one node. Expected: no rows.
MATCH (n)
WITH n.id AS id, count(n) AS c
WHERE c > 1
RETURN id, c
