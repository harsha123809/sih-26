"""Env-Attention U-Net: the oil-type classification model.

Vision branch: ResNet-34 encoder over a 4-channel 512x512 input
    [sigma0_VV_dB, sigma0_VH_dB, VV/VH_ratio_dB, wind_speed_map]
Context branch: MLP over global scalars, producing FiLM (gamma, beta) that
    MULTIPLICATIVELY modulates the bottleneck feature maps — this lets
    environmental context suppress oil-feature channels outright rather than
    merely nudging them, which is what a concatenation-based fusion cannot do.
Decoder: U-Net with skip connections, softmax over 6 classes.

This module defines the real, trainable architecture. No trained weights are
shipped (no GPU/training corpus was available at build time — see
core/ml/infer.py for the SIMULATION_MODE inference path used by the API).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torchvision.models import resnet34
    _HAS_TORCHVISION = True
except ImportError:  # pragma: no cover - torchvision optional at runtime
    _HAS_TORCHVISION = False

NUM_CLASSES = 6
CLASS_NAMES = ["open_water", "crude_oil", "heavy_fuel_oil", "look_alike", "ship", "land"]
CONTEXT_DIM = 7  # [wind_speed, wind_dir_sin, wind_dir_cos, sst, incidence_angle, wave_height, has_polarimetry]

# Fill value for the VH and VV/VH channels when a product carries no
# cross-polarisation band. Deliberately far outside the range real sigma0 dB
# ever takes (roughly -40..+5), so the network can learn "this channel is
# absent" as a distinct state rather than confusing it for a real weak return.
# Paired with has_polarimetry=0 in the context vector, and with the API
# reporting oil type as UNRESOLVED — never a guess between crude and HFO.
VH_SENTINEL_VALUE = -99.0


class ConvBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ContextBranch(nn.Module):
    """MLP over environmental scalars producing FiLM (gamma, beta) vectors."""

    def __init__(self, in_dim: int = CONTEXT_DIM, feature_dim: int = 512, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, hidden),
            nn.ReLU(inplace=True),
        )
        self.to_gamma = nn.Linear(hidden, feature_dim)
        self.to_beta = nn.Linear(hidden, feature_dim)

    def forward(self, context: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.net(context)
        gamma = self.to_gamma(h)
        beta = self.to_beta(h)
        return gamma, beta


class EnvAttentionUNet(nn.Module):
    """ResNet-34 encoder + FiLM-gated bottleneck + U-Net decoder."""

    def __init__(self, in_channels: int = 4, num_classes: int = NUM_CLASSES):
        super().__init__()
        if _HAS_TORCHVISION:
            backbone = resnet34(weights=None)
            backbone.conv1 = nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False)
            self.stem = nn.Sequential(backbone.conv1, backbone.bn1, backbone.relu)
            self.pool = backbone.maxpool
            self.layer1 = backbone.layer1  # 64
            self.layer2 = backbone.layer2  # 128
            self.layer3 = backbone.layer3  # 256
            self.layer4 = backbone.layer4  # 512 (bottleneck)
        else:  # lightweight fallback so the module still imports without torchvision
            self.stem = ConvBlock(in_channels, 64)
            self.pool = nn.MaxPool2d(2)
            self.layer1 = ConvBlock(64, 64)
            self.layer2 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(64, 128))
            self.layer3 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(128, 256))
            self.layer4 = nn.Sequential(nn.MaxPool2d(2), ConvBlock(256, 512))

        self.context_branch = ContextBranch(feature_dim=512)

        self.up3 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec3 = ConvBlock(512, 256)
        self.up2 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec2 = ConvBlock(256, 128)
        self.up1 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec1 = ConvBlock(128, 64)
        self.up0 = nn.ConvTranspose2d(64, 32, 2, stride=2)
        self.dec0 = ConvBlock(32, 32)
        self.final_up = nn.ConvTranspose2d(32, 32, 2, stride=2)

        self.seg_head = nn.Conv2d(32, num_classes, 1)
        # Auxiliary scene-level classifier head (0.1 weight in the loss)
        self.aux_head = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(512, num_classes))

        # Temperature-scaling calibration parameter (learned post-hoc)
        self.log_temperature = nn.Parameter(torch.zeros(1))

    def forward(self, x: torch.Tensor, context: torch.Tensor) -> dict[str, torch.Tensor]:
        s0 = self.stem(x)
        s1 = self.layer1(self.pool(s0)) if _HAS_TORCHVISION else self.layer1(self.pool(s0))
        s2 = self.layer2(s1)
        s3 = self.layer3(s2)
        z = self.layer4(s3)  # bottleneck, shape [B, 512, H/32, W/32]

        gamma, beta = self.context_branch(context)
        gamma = gamma.unsqueeze(-1).unsqueeze(-1)
        beta = beta.unsqueeze(-1).unsqueeze(-1)
        z = gamma * z + beta  # FiLM: multiplicative modulation, can suppress channels to ~0

        d3 = self.dec3(torch.cat([self.up3(z), s3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), s2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), s1], dim=1))
        d0 = self.dec0(self.up0(d1))
        d_full = self.final_up(d0)

        logits = self.seg_head(d_full)
        logits = F.interpolate(logits, size=x.shape[-2:], mode="bilinear", align_corners=False)
        calibrated = logits / self.log_temperature.exp()

        aux_logits = self.aux_head(z)

        return {"seg_logits": calibrated, "aux_logits": aux_logits}


def build_context_vector(
    wind_speed: float,
    wind_dir_deg: float,
    sst_c: float,
    incidence_angle_deg: float,
    wave_height_m: float,
    has_polarimetry: bool,
) -> torch.Tensor:
    import math

    rad = math.radians(wind_dir_deg)
    return torch.tensor(
        [[wind_speed, math.sin(rad), math.cos(rad), sst_c, incidence_angle_deg, wave_height_m, float(has_polarimetry)]],
        dtype=torch.float32,
    )
