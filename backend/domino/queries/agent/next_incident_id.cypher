// Number of incidents so far, to mint the next INC-#### id.
MATCH (i:Incident)
RETURN count(i) AS n
