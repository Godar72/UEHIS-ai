# UEHIS – Feature Engineering Module
# Semantic segmentation, NDVI/morphology features, and OSM overlay.

from feature_engineering.unet import UNet, NUM_CLASSES, CLASS_NAMES
from feature_engineering.train import train_model, PatchDataset
from feature_engineering.predict import predict_composite
from feature_engineering.overlay import vectorise_segmentation, merge_with_buildings

__all__ = [
    "UNet",
    "NUM_CLASSES",
    "CLASS_NAMES",
    "train_model",
    "PatchDataset",
    "predict_composite",
    "vectorise_segmentation",
    "merge_with_buildings",
]
