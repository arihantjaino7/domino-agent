// Every id in the world, for "did you mean" suggestions on unknown ids. Small world; capped.
MATCH (n) WHERE n.id IS NOT NULL
RETURN n.id AS id
LIMIT 5000
