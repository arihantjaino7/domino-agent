// Edge count per relationship type. The edge is aliased so every parallel edge is counted.
MATCH ()-[r]->()
RETURN type(r) AS type, count(r) AS n
