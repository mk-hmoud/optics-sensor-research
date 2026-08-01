from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Material:
    name: str
    refractive_index: Optional[float] = None
    color: str = 'white'  # For visualization


@dataclass
class GeometricShape:
    center: Point
    material: Material
    rotation: float = 0.0  # degrees


@dataclass
class Circle(GeometricShape):
    radius: float = 0.0


@dataclass
class Ellipse(GeometricShape):
    radius_x: float = 0.0
    radius_y: float = 0.0


@dataclass
class Layer:
    """Represents a concentric coating layer on the fiber."""
    material: Material
    thickness: float  # µm
    location: str     # 'internal' or 'external'


@dataclass
class FiberGeometry:
    background_material: Material
    radius: float                                        # µm: total cladding radius
    shapes: List[Union[Circle, Ellipse]] = field(default_factory=list)
    d_shape_distance: Optional[float] = None            # µm: distance from center to flat side
    external_layers: List[Layer] = field(default_factory=list)  # concentric rings outside radius

    def add_shape(self, shape: GeometricShape):
        self.shapes.append(shape)
