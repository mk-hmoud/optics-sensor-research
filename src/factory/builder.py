import math
import numpy as np
from src.design.geometry import FiberGeometry, Circle, Ellipse, Point, Material, Layer
from src.design.parameter_space import FiberSpec


class FiberBuilder:
    def __init__(self, spec: FiberSpec):
        self.spec = spec
        # Fixed fiber radius to fit within -10 to 10 um (Target R=10 total)
        self.fiber_radius = 7.0  # µm

    def build(self) -> FiberGeometry:
        bg_material = Material(name=self.spec.background.material)

        fiber = FiberGeometry(
            background_material=bg_material,
            radius=self.fiber_radius,
        )

        # 1. Generate Lattice
        self._generate_lattice(fiber)

        # 2. Add External Layers
        # Gold layer: convert nm → µm
        au_thickness_um = self.spec.plasmonic_layer.thickness_nm / 1000.0
        fiber.external_layers.append(Layer(
            material=Material(name='Au', color='gold'),
            thickness=au_thickness_um,  # µm
            location='external',
        ))

        # Analyte channel: half the lattice pitch wide
        analyte_thickness_um = self.spec.lattice.pitch / 2.0  # µm
        fiber.external_layers.append(Layer(
            material=Material(name='Analyte', color='cyan'),
            thickness=analyte_thickness_um,  # µm
            location='external',
        ))

        # PML buffer
        pml_thickness_um = 1.4  # µm: fixed — computational, not physical
        fiber.external_layers.append(Layer(
            material=Material(name='PML', color='plum'),
            thickness=pml_thickness_um,  # µm
            location='external',
        ))

        return fiber

    def _generate_lattice(self, fiber: FiberGeometry):
        pitch = self.spec.lattice.pitch
        rings = max(3, self.spec.lattice.num_rings)

        # Hole diameters as fractions of pitch (from literature)
        d_c = 0.49 * pitch
        d_1 = 0.28 * pitch
        d_2 = 0.90 * pitch
        d_3 = 0.97 * pitch

        # Central hole
        fiber.add_shape(Circle(
            center=Point(0, 0),
            material=Material(name='Air', color='white'),
            radius=d_c / 2.0,
        ))

        # Rings
        for r in range(1, rings + 1):
            if r == 1:
                base_radius = d_1 / 2.0
            elif r == 2:
                base_radius = d_2 / 2.0
            else:
                base_radius = d_3 / 2.0

            for (x, y) in self._get_hex_ring_positions(r, pitch):
                fiber.add_shape(Circle(
                    center=Point(x, y),
                    material=Material(name='Air', color='white'),
                    radius=base_radius,
                ))

    def _get_hex_ring_positions(self, r, pitch):
        positions = []
        move_dirs = [
            (-0.5 * pitch,  math.sqrt(3) / 2 * pitch),
            (-1.0 * pitch,  0),
            (-0.5 * pitch, -math.sqrt(3) / 2 * pitch),
            ( 0.5 * pitch, -math.sqrt(3) / 2 * pitch),
            ( 1.0 * pitch,  0),
            ( 0.5 * pitch,  math.sqrt(3) / 2 * pitch),
        ]
        cx, cy = r * pitch, 0
        for i in range(6):
            dx, dy = move_dirs[i]
            for _ in range(r):
                positions.append((cx, cy))
                cx += dx
                cy += dy
        return positions
