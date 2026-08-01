import matplotlib.pyplot as plt
from matplotlib.patches import Circle as pltCircle, Ellipse as pltEllipse
from src.design.geometry import FiberGeometry, Circle, Ellipse


class FiberPlotter:
    def __init__(self, fiber: FiberGeometry):
        self.fiber = fiber

    def plot(self, save_path: str = None):
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_aspect('equal')

        # 1. External layers — build cumulative radii, then draw outside-in
        r_start = self.fiber.radius
        layer_radii = []
        for layer in self.fiber.external_layers:
            r_end = r_start + layer.thickness
            layer_radii.append((r_start, r_end, layer))
            r_start = r_end

        max_r = r_start  # outermost edge

        for (_r_in, r_out, layer) in reversed(layer_radii):
            color_map = {'PML': 'thistle', 'Analyte': 'lightcyan', 'Au': 'gold'}
            color = color_map.get(layer.material.name, layer.material.color)
            ax.add_patch(pltCircle((0, 0), r_out, color=color, label=layer.material.name))

        # 2. Fiber cladding (covers the centre of the innermost external layer)
        ax.add_patch(pltCircle((0, 0), self.fiber.radius, color='wheat', alpha=0.5, label='Silica'))

        # 3. Air holes
        for shape in self.fiber.shapes:
            if isinstance(shape, Circle):
                patch = pltCircle(
                    (shape.center.x, shape.center.y), shape.radius,
                    color='white', ec='black', lw=0.5,
                )
            elif isinstance(shape, Ellipse):
                patch = pltEllipse(
                    (shape.center.x, shape.center.y),
                    width=shape.radius_x * 2, height=shape.radius_y * 2,
                    angle=shape.rotation,
                    color='white', ec='black', lw=0.5,
                )
            else:
                continue
            ax.add_patch(patch)

        limit = max_r * 1.1
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        plt.title("Sensor Design Preview (Concentric)")

        if save_path:
            plt.savefig(save_path)
            print(f"Saved design to {save_path}")
        else:
            plt.show()

        plt.close(fig)
