import mph
import os
from src.design.parameter_space import FiberSpec
from src.factory.builder import FiberBuilder
from src.factory.comsol_builder import COMSOLBuilder

def main():
    print("=== PCF-SPR COMSOL Generator ===")

    print("Connecting to COMSOL... (make sure COMSOL is installed)")
    try:
        client = mph.start(graphics=True)
    except Exception as e:
        print(f"FAILED to start COMSOL: {e}")
        print("\nEnsure COMSOL is in your System Path or restart the script.")
        return

    model_name = 'PCF_Generated_Design'
    model = client.create(model_name)
    print(f"Created new model: {model_name}")

    print("Sampling design from parameter space...")
    spec = FiberSpec.random()

    builder = FiberBuilder(spec)
    fiber = builder.build()
    print(f"Generated design with {len(fiber.shapes)} holes.")

    print("Sending geometry and materials to COMSOL... this may take a moment.")
    try:
        comsol_builder = COMSOLBuilder(model)
        comsol_builder.build(fiber, spec)
        print("Model construction complete.")
    except Exception as e:
        print(f"Error during COMSOL build: {e}")

    output_path = os.path.abspath("data/last_design.mph")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    model.save(output_path)
    print(f"\nSUCCESS! Model saved to: {output_path}")
    print("You can now open this file in the COMSOL GUI.")

if __name__ == "__main__":
    main()
