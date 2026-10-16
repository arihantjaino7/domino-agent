// Seed loader: Physical sites: cell fabs, pack lines, OSATs, module lines. One batch of rows per call; returns the count for the loader receipt.
UNWIND $rows AS r
CREATE (n:Site:Place)
SET n = r
RETURN count(n) AS created
