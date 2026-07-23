"""Small CIFAR-10 CNN shared by the serving app and the weight-seeding script. Kept intentionally
small — the system measures drift/latency/distribution shifts, not classifier accuracy."""

import io

import torch
from PIL import Image
from torch import nn

CLASSES = [
    "airplane", "automobile", "bird", "cat", "deer",
    "dog", "frog", "horse", "ship", "truck",
]
NUM_CLASSES = len(CLASSES)

# CIFAR-10 channel normalization.
_MEAN = torch.tensor([0.4914, 0.4822, 0.4465]).view(3, 1, 1)
_STD = torch.tensor([0.2470, 0.2435, 0.2616]).view(3, 1, 1)


class SmallCNN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),  # 32 -> 16
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),  # 16 -> 8
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 8 * 8, 128),
            nn.ReLU(),
            nn.Linear(128, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def preprocess(image_bytes: bytes) -> torch.Tensor:
    """PNG/JPEG bytes -> normalized (1, 3, 32, 32) tensor."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((32, 32))
    arr = torch.frombuffer(bytearray(img.tobytes()), dtype=torch.uint8).float() / 255.0
    chw = arr.view(32, 32, 3).permute(2, 0, 1)
    return ((chw - _MEAN) / _STD).unsqueeze(0)
