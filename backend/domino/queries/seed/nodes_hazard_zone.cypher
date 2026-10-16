// Seed loader: Correlated hazard areas (flood, quake, typhoon, hurricane). One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:HazardZone:Place)
SET n = r
RETURN count(n) AS created
