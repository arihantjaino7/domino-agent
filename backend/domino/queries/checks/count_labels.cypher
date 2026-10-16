// Node count per label set (Site nodes also carry :Place). Used by `make seed` and the loader receipt.
MATCH (n)
RETURN labels(n) AS labels, count(n) AS n
