"""
PCF-SPR Fiber Designer
======================
A library for designing and visualising Photonic Crystal Fiber
Surface Plasmon Resonance (PCF-SPR) sensor cross-sections.

Typical usage
-------------
    from src import FiberSpec, FiberBuilder, FiberPlotter

    spec = FiberSpec.random()          # randomised design
    fiber = FiberBuilder(spec).build() # abstract geometry
    FiberPlotter(fiber).plot()         # visualise

For COMSOL export (requires mph / COMSOL installation):
    from src.factory.comsol_builder import COMSOLBuilder
"""

from src.design.parameter_space import FiberSpec
from src.design.geometry import FiberGeometry
from src.factory.builder import FiberBuilder
from src.visualization.plotter import FiberPlotter

__all__ = [
    "FiberSpec",
    "FiberGeometry",
    "FiberBuilder",
    "FiberPlotter",
]
