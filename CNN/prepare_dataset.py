import os
import shutil
import glob
from sklearn.model_selection import train_test_split

# --- Configuration ---
SOURCE_DIR = 'labeled_images' 
DEST_DIR = 'data' 
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


def main():
    """
    Reads images from the source directory, splits them into train, val, and test sets,
    and copies them into the destination directory with the correct structure.
    """
    print("--- Starting Dataset Preparation ---")

    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' not found.")
        print("Please create it and place your labeled subdirectories (e.g., 'fundamental', 'higher', 'lower') inside.")
        return

    if os.path.exists(DEST_DIR):
        shutil.rmtree(DEST_DIR)
        print(f"Removed existing '{DEST_DIR}' directory.")
    
    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"Created destination directory '{DEST_DIR}'.")

    class_names = [d for d in os.listdir(SOURCE_DIR) if os.path.isdir(os.path.join(SOURCE_DIR, d))]
    if len(class_names) < 2:
        print(f"Error: Found only {len(class_names)} class subdirectories in '{SOURCE_DIR}'. Expected at least 2.")
        return
        
    print(f"Found classes: {class_names}")

    all_files = []
    labels = []
    for class_name in class_names:
        class_dir = os.path.join(SOURCE_DIR, class_name)
        image_files = glob.glob(os.path.join(class_dir, '*.[pP][nN][gG]')) + \
                      glob.glob(os.path.join(class_dir, '*.[jJ][pP][gG]')) + \
                      glob.glob(os.path.join(class_dir, '*.[jJ][pP][eE][gG]'))
        
        all_files.extend(image_files)
        labels.extend([class_name] * len(image_files))

    if not all_files:
        print("Error: No image files found in the source directories.")
        return

    print(f"Found a total of {len(all_files)} images.")

    X_train, X_temp, y_train, y_temp = train_test_split(
        all_files, labels, test_size=(1 - TRAIN_RATIO), random_state=42, stratify=labels)

    val_test_ratio = TEST_RATIO / (VAL_RATIO + TEST_RATIO)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=val_test_ratio, random_state=42, stratify=y_temp)

    print("\nSplitting data into sets:")
    print(f"  - Training:   {len(X_train)} images")
    print(f"  - Validation: {len(X_val)} images")
    print(f"  - Test:       {len(X_test)} images")

    def copy_files(files, labels, split_name):
        print(f"\nCopying '{split_name}' files...")
        for file, label in zip(files, labels):
            dest_path = os.path.join(DEST_DIR, split_name, label)
            os.makedirs(dest_path, exist_ok=True)
            shutil.copy(file, dest_path)
        print(f"Finished copying {len(files)} files.")

    copy_files(X_train, y_train, 'train')
    copy_files(X_val, y_val, 'val')
    copy_files(X_test, y_test, 'test')
    
    print("\n--- Dataset preparation complete! ---")
    print(f"Your dataset is now ready in the '{DEST_DIR}/' directory.")

if __name__ == '__main__':
    main()
