from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class LatticeSpec:
    type: Literal['hex', 'square', 'kagome', 'fractal_leaf'] = 'hex'
    pitch: float = 1.5          # µm
    num_rings: int = 3
    d_shape_cut: float = 0.0    # µm: depth of side polishing (0 = full fiber)
    corner_radius: float = 0.0  # µm: rounds sharp polygon corners


@dataclass
class GlobalPerturbationSpec:
    scaling: float = 1.0    # uniform scaling factor (manufacturing tolerance)
    rotation: float = 0.0   # degrees


@dataclass
class LocalNoiseSpec:
    position_jitter: float = 0.0     # µm: random offset from grid per hole
    radius_noise: float = 0.0        # µm: variation in hole size per hole
    ellipticity: float = 1.0         # aspect ratio (1.0 = perfect circle)
    ellipse_rotation: float = 0.0    # degrees: orientation of oval
    interface_roughness_nm: float = 0.0  # nm: RMS roughness on metal surfaces


@dataclass
class TopologicalDefectsSpec:
    missing_holes_prob: float = 0.0  # probability to delete a hole
    merged_holes_prob: float = 0.0   # probability to join neighbors (slot waveguide)
    core_type: Literal['solid', 'hollow', 'defect_cluster'] = 'solid'


@dataclass
class AdhesionLayerSpec:
    material: Literal['none', 'Ti', 'Cr'] = 'none'
    thickness_nm: float = 0.0  # nm


@dataclass
class ProtectiveLayerSpec:
    material: Literal['none', 'graphene', 'MgF2'] = 'none'
    thickness_nm: float = 0.0  # nm


@dataclass
class PlasmonicLayerSpec:
    metal_type: Literal['Au', 'Ag', 'Al', 'Cu', 'TiN'] = 'Au'
    thickness_nm: float = 40.0      # nm: CRITICAL variable for SPR
    grain_size_nm: float = 50.0     # nm: affects electron damping (Drude-Lorentz model)
    coating_location: Literal[
        'selective_holes', 'external_d_side', 'internal_capillaries'
    ] = 'external_d_side'
    coating_uniformity: float = 1.0  # 1.0 = perfect, 0.8 = rough deposition
    adhesion_layer: AdhesionLayerSpec = field(default_factory=AdhesionLayerSpec)
    protective_layer: ProtectiveLayerSpec = field(default_factory=ProtectiveLayerSpec)


@dataclass
class AnalyteSpec:
    refractive_index: float = 1.33      # water=1.33, serum=1.35, oil=1.40+
    temp_coefficient: float = -2.5e-4   # dn/dT (thermo-optic coefficient)
    fill_pattern: Literal[
        'all_holes', 'adjacent_to_metal', 'external_only'
    ] = 'all_holes'


@dataclass
class BackgroundSpec:
    material: str = 'Silica_Sellmeier'
    dopant_level: float = 0.0   # % GeO2: optionally modifies core index


@dataclass
class SpectralSpec:
    wavelength_start_nm: float = 500.0   # nm
    wavelength_end_nm: float = 2000.0    # nm
    step_nm: float = 2.0                 # nm: fine step required for Q-factor


@dataclass
class FiberSpec:
    """
    Complete specification for a PCF-SPR fiber design.

    All length units are explicit in field names (_nm for nanometres, _um for
    micrometres). Use FiberSpec.random() to draw a randomised design from the
    full design space.
    """
    lattice: LatticeSpec = field(default_factory=LatticeSpec)
    global_perturbation: GlobalPerturbationSpec = field(default_factory=GlobalPerturbationSpec)
    local_noise: LocalNoiseSpec = field(default_factory=LocalNoiseSpec)
    topological_defects: TopologicalDefectsSpec = field(default_factory=TopologicalDefectsSpec)
    plasmonic_layer: PlasmonicLayerSpec = field(default_factory=PlasmonicLayerSpec)
    analyte: AnalyteSpec = field(default_factory=AnalyteSpec)
    background: BackgroundSpec = field(default_factory=BackgroundSpec)
    spectral: SpectralSpec = field(default_factory=SpectralSpec)
    temperature_c: float = 25.0  # Celsius

    @classmethod
    def random(cls) -> FiberSpec:
        """Sample a randomised fiber design from the full design space."""
        return cls(
            lattice=LatticeSpec(
                type=random.choice(['hex', 'square', 'kagome', 'fractal_leaf']),
                pitch=random.uniform(1.2, 1.8),
                num_rings=random.randint(2, 3),
                d_shape_cut=random.uniform(0.0, 30.0),
                corner_radius=random.uniform(0.0, 0.2),
            ),
            global_perturbation=GlobalPerturbationSpec(
                scaling=random.uniform(0.85, 1.15),
                rotation=random.uniform(0.0, 90.0),
            ),
            local_noise=LocalNoiseSpec(
                position_jitter=random.uniform(0.0, 0.15),
                radius_noise=random.uniform(0.0, 0.05),
                ellipticity=random.uniform(0.8, 1.2),
                ellipse_rotation=random.uniform(0.0, 180.0),
                interface_roughness_nm=random.uniform(0.0, 5.0),
            ),
            topological_defects=TopologicalDefectsSpec(
                missing_holes_prob=random.uniform(0.0, 0.1),
                merged_holes_prob=random.uniform(0.0, 0.05),
                core_type=random.choice(['solid', 'hollow', 'defect_cluster']),
            ),
            plasmonic_layer=PlasmonicLayerSpec(
                metal_type=random.choice(['Au', 'Ag', 'Al', 'Cu', 'TiN']),
                thickness_nm=random.uniform(20.0, 60.0),
                grain_size_nm=random.uniform(10.0, 100.0),
                coating_location=random.choice([
                    'selective_holes', 'external_d_side', 'internal_capillaries',
                ]),
                coating_uniformity=random.uniform(0.8, 1.0),
                adhesion_layer=AdhesionLayerSpec(
                    material=random.choice(['none', 'Ti', 'Cr']),
                    thickness_nm=random.uniform(0.0, 5.0),
                ),
                protective_layer=ProtectiveLayerSpec(
                    material=random.choice(['none', 'graphene', 'MgF2']),
                    thickness_nm=random.uniform(0.0, 10.0),
                ),
            ),
            analyte=AnalyteSpec(
                refractive_index=random.uniform(1.33, 1.42),
                temp_coefficient=random.uniform(-4e-4, -1e-4),
                fill_pattern=random.choice([
                    'all_holes', 'adjacent_to_metal', 'external_only',
                ]),
            ),
            background=BackgroundSpec(
                material='Silica_Sellmeier',
                dopant_level=random.uniform(0.0, 0.05),
            ),
            spectral=SpectralSpec(
                wavelength_start_nm=500.0,
                wavelength_end_nm=2000.0,
                step_nm=2.0,
            ),
            temperature_c=random.uniform(20.0, 80.0),
        )
