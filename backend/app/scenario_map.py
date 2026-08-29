"""Which vessel MMSIs are attribution candidates for each seeded scene. In a
production system this would be a PostGIS spatial query (vessels whose track
intersects the drift cone in the plausible release window); for the seeded
demo the geometry is fixed per scene, so the candidate set is fixed too.
"""

CANDIDATE_MMSIS_BY_SCENE: dict[str, list[str]] = {
    "scene-01-crude-tanker": ["431003001"],
    "scene-02-hfo-container": ["412345678"],
    "scene-03-low-wind-suppressed": ["440221100"],
    "scene-04-spoofing": ["419876543"],
    # Deliberately empty: the vessel here is fully dark, no AIS track exists
    # to intersect the drift cone. That absence is itself the finding.
    "scene-05-dark-ship": [],
    "scene-06-crude-excluded-feeder": ["477001122"],
}
