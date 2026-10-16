// Seed loader: Parts and sub-parts (multi-level BOM). One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Component)
SET n = r
RETURN count(n) AS created
