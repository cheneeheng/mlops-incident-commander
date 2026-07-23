"""Generate two CNN checkpoints into weights/: a deterministic 'good' model and a deliberately
degraded 'bad' model for the bad-deploy fault. Real training is out of scope — the app needs a
working good/bad pair, not accuracy. See DECISION_LOG entry 2.

Run: uv run python scripts/seed_weights.py
"""

from pathlib import Path

import torch

from serving.app.cnn import SmallCNN

WEIGHTS_DIR = Path("weights")


def main() -> None:
    WEIGHTS_DIR.mkdir(exist_ok=True)

    torch.manual_seed(42)
    good = SmallCNN()
    torch.save(good.state_dict(), WEIGHTS_DIR / "v1.0-good.pt")

    # Degrade the final layer so predictions collapse toward uniform / low confidence.
    bad = SmallCNN()
    bad.load_state_dict(good.state_dict())
    with torch.no_grad():
        final = bad.classifier[-1]
        final.weight.zero_()
        final.bias.zero_()
    torch.save(bad.state_dict(), WEIGHTS_DIR / "v1.1-bad.pt")

    print(f"wrote {WEIGHTS_DIR/'v1.0-good.pt'} and {WEIGHTS_DIR/'v1.1-bad.pt'}")


if __name__ == "__main__":
    main()
