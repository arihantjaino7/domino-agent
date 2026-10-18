// Geographic places used for deterministic live-alert screening. Read only.
MATCH (p:Place)
WHERE (p:Site OR p:Plant OR p:Port OR p:Region) AND p.lat IS NOT NULL AND p.lng IS NOT NULL
RETURN p.id AS id, p.name AS name, p.lat AS lat, p.lng AS lng, p.tier AS tier,
       CASE WHEN p:Site THEN 'Site' WHEN p:Plant THEN 'Plant' WHEN p:Port THEN 'Port' ELSE 'Region' END AS kind
ORDER BY id
