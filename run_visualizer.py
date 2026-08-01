import os
import sys
from src.design.parameter_space import FiberSpec
from src.factory.builder import FiberBuilder
from src.visualization.plotter import FiberPlotter

def main():
    batch_size = 1
    if len(sys.argv) > 1:
        try:
            batch_size = int(sys.argv[1])
        except ValueError:
            print("Invalid batch size provided. Using default: 1")

    print(f"Generating batch of {batch_size} designs...")

    output_dir = 'data/visualization'
    os.makedirs(output_dir, exist_ok=True)

    for i in range(batch_size):
        spec = FiberSpec.random()

        builder = FiberBuilder(spec)
        fiber = builder.build()

        filename = f'design_{i+1:03d}.png'
        output_path = os.path.join(output_dir, filename)

        plotter = FiberPlotter(fiber)
        plotter.plot(save_path=output_path)

        print(f"[{i+1}/{batch_size}] Saved {filename} "
              f"(Lattice: {spec.lattice.type}, Holes: {len(fiber.shapes)})")

    print(f"\nBatch generation complete. Check {output_dir}")

if __name__ == "__main__":
    main()
