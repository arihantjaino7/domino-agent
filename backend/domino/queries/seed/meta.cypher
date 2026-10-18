// World metadata. world_version is bumped by every later write.
CREATE (m:Meta {id: 'META', world_version: 0, seed: $seed, fingerprint: $fingerprint})
RETURN count(m) AS created
