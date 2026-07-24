"""Seed the two deploys and the reference profile ITER_01 needs. Idempotent — safe to re-run.

- v1.0-good: active, not faulty (the healthy baseline model).
- v1.1-bad:  inactive, faulty (activated by the bad_deploy injection).
- reference_profile for v1.0-good: uniform class distribution + a baseline mean_confidence, the
  clean-warm-up baseline the aggregator scores PSI against.

Run: uv run python scripts/seed_db.py   (or `make seed-db`; `make seed` also seeds weights)
"""

import asyncio

from backend.app.db.models import Deploy, ReferenceProfile
from backend.app.db.queries import get_deploy_by_version, get_reference_profile
from backend.app.db.session import SessionLocal
from serving.app.cnn import NUM_CLASSES

# Illustrative clean-run baseline; not used by the ITER_01 aggregator (which scores PSI on the class
# distribution), stored for the confidence-drop signal that later iterations read.
BASELINE_MEAN_CONFIDENCE = 0.5

_DEPLOYS: list[tuple[str, str, bool, bool]] = [
    # (model_version, artifact_path, is_active, is_faulty)
    ("v1.0-good", "weights/v1.0-good.pt", True, False),
    ("v1.1-bad", "weights/v1.1-bad.pt", False, True),
]


async def seed() -> None:
    async with SessionLocal() as db:
        for model_version, artifact_path, is_active, is_faulty in _DEPLOYS:
            if await get_deploy_by_version(db, model_version) is None:
                db.add(
                    Deploy(
                        model_version=model_version,
                        artifact_path=artifact_path,
                        is_active=is_active,
                        is_faulty=is_faulty,
                    )
                )
                print(f"+ deploy {model_version} (active={is_active}, faulty={is_faulty})")
            else:
                print(f"= deploy {model_version} already present")

        if await get_reference_profile(db, "v1.0-good") is None:
            db.add(
                ReferenceProfile(
                    model_version="v1.0-good",
                    class_distribution={str(i): 1.0 / NUM_CLASSES for i in range(NUM_CLASSES)},
                    mean_confidence=BASELINE_MEAN_CONFIDENCE,
                )
            )
            print("+ reference_profile v1.0-good (uniform baseline)")
        else:
            print("= reference_profile v1.0-good already present")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
