"""Route safety scoring. SAFETY-CRITICAL
Pure functions only — no hardware, no I/O — so this, the part that decides
whether a corridor is usable, is the most heavily tested code in the app.
"""


def compute_safety_score(detections: list[dict],
                         person_penalty: int = 30,
                         confidence_floor: float = 0.4) -> int:
    """Score 0-100 from a list of detections [{'label','confidence'}, ...].

    Placeholder fusion model: start at 100, subtract person_penalty per
    confident person detection (crowds block corridors). Extend with
    rubble/fire/vehicle classes as the detector grows.
    """
    score = 100
    for det in detections:
        if det.get("label") == "person" and det.get("confidence", 0) >= confidence_floor:
            score -= person_penalty
    return max(0, min(100, score))


def verdict(score: int, threshold: int = 70) -> str:
    """Map score to an operator verdict: USABLE / DEGRADED / BLOCKED."""
    if score > threshold:
        return "USABLE"
    if score > threshold // 2:
        return "DEGRADED"
    return "BLOCKED"


def verdict_colour(v: str) -> tuple[int, int, int]:
    """LED ring colour per verdict — the field operator's at-a-glance signal."""
    return {"USABLE": (0, 200, 0),
            "DEGRADED": (255, 120, 0),
            "BLOCKED": (200, 0, 0)}.get(v, (0, 80, 255))
