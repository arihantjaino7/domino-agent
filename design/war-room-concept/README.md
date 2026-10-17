# War-room concept

The standalone design the author approved before it was merged into `frontend/`. It reads `data.js`, a capture of one scripted
(dry-run) monsoon run plus `/api/graph`, so it works without the backend. Open it with the `war-room-concept` preview
(`python -m http.server 5180 --directory design/war-room-concept`). Query flags for review: `?approved=1`, `?factory=<site id>`, `?shot=1`
(no animations). The real app in `frontend/` renders the same design from live engine events instead.
