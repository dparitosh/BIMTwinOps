"""
PointNet S3DIS - Point Cloud Semantic Segmentation

This package provides semantic segmentation for 3D point clouds using PointNet.
Used for classifying building elements in BIM point cloud data.
"""

from .online_segmentation import process_uploaded_array

__all__ = ['process_uploaded_array']
