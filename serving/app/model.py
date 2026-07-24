"""Classifier wrapper: loads the active deploy's CNN weights and runs inference. The 5s poller in
main.py calls load_active when the active deploy version changes."""

import torch
import torch.nn.functional as F

from serving.app.cnn import SmallCNN, preprocess


class Classifier:
    """Holds the loaded CNN and the version it was loaded from. Not loaded until load_active runs."""

    def __init__(self) -> None:
        self._model: SmallCNN | None = None
        self.model_version: str = ""

    def load_active(self, model_version: str, artifact_path: str) -> None:
        model = SmallCNN()
        # weights_only=True: we only ever load our own state_dict checkpoints — never unpickle code.
        model.load_state_dict(torch.load(artifact_path, map_location="cpu", weights_only=True))
        model.eval()
        self._model = model
        self.model_version = model_version

    def predict(self, image_bytes: bytes) -> tuple[int, float]:
        if self._model is None:
            raise RuntimeError("no active model loaded")
        tensor = preprocess(image_bytes)
        with torch.no_grad():
            probs = F.softmax(self._model(tensor), dim=1)
            confidence, predicted = torch.max(probs, dim=1)
        return int(predicted.item()), float(confidence.item())


classifier = Classifier()
