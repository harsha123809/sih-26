"""Training loss: 0.6 x weighted focal loss + 0.3 x soft dice + 0.1 x auxiliary
scene-level classifier head. Used only by the (not-yet-run) training script —
the API never trains at request time."""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

# Background (open_water) is by far the most common class in any real scene;
# oil classes are up-weighted so the network isn't rewarded for predicting
# "open water" everywhere.
CLASS_WEIGHTS = torch.tensor([0.5, 3.0, 3.0, 1.5, 1.0, 0.5])


def weighted_focal_loss(logits: torch.Tensor, targets: torch.Tensor, gamma: float = 2.0, weights: torch.Tensor = CLASS_WEIGHTS) -> torch.Tensor:
    log_probs = F.log_softmax(logits, dim=1)
    probs = log_probs.exp()
    targets_one_hot = F.one_hot(targets, num_classes=logits.shape[1]).permute(0, 3, 1, 2).float()
    pt = (probs * targets_one_hot).sum(dim=1)
    focal_term = (1 - pt).clamp(min=1e-6) ** gamma
    ce = -(log_probs * targets_one_hot).sum(dim=1)
    w = weights.to(logits.device)[targets]
    return (w * focal_term * ce).mean()


def soft_dice_loss(logits: torch.Tensor, targets: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    probs = F.softmax(logits, dim=1)
    targets_one_hot = F.one_hot(targets, num_classes=logits.shape[1]).permute(0, 3, 1, 2).float()
    dims = (0, 2, 3)
    intersection = (probs * targets_one_hot).sum(dims)
    union = probs.sum(dims) + targets_one_hot.sum(dims)
    dice = (2 * intersection + eps) / (union + eps)
    return 1.0 - dice.mean()


def combined_loss(
    seg_logits: torch.Tensor,
    seg_targets: torch.Tensor,
    aux_logits: torch.Tensor,
    aux_targets: torch.Tensor,
) -> torch.Tensor:
    focal = weighted_focal_loss(seg_logits, seg_targets)
    dice = soft_dice_loss(seg_logits, seg_targets)
    aux = F.cross_entropy(aux_logits, aux_targets)
    return 0.6 * focal + 0.3 * dice + 0.1 * aux
