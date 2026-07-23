"""Classifier wrapper. Stub at SKELETON; real CNN load/predict + active-deploy tracking in ITER_01."""


class Classifier:
    """Holds the active model version and runs inference. SKELETON returns a fixed stub prediction."""

    def __init__(self) -> None:
        self.model_version: str = "v1.0-good"

    def load_active(self, model_version: str, artifact_path: str) -> None:
        # stub — real weight loading in ITER_01
        self.model_version = model_version

    def predict(self, image_bytes: bytes) -> tuple[int, float]:
        # stub — real CNN forward pass in ITER_01
        return 0, 0.5


classifier = Classifier()
