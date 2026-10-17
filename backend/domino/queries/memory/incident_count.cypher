// How many incidents memory holds (memory graph), for the next memory incident id.
MATCH (i:Incident)
RETURN count(i) AS n
