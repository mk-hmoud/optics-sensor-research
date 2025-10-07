import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import os
import random
import matplotlib.pyplot as plt

# --- Configuration ---
MODEL_PATH = 'mode_cnn_model.pth'
DATA_DIR = 'data'
IMG_SIZE = 64
NUM_PREDICTIONS = 8

class ModeCNN(nn.Module):
    def __init__(self, num_classes=3):
        super(ModeCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.fc1 = nn.Linear(64 * (IMG_SIZE // 4) * (IMG_SIZE // 4), 64)
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = x.view(-1, 64 * (IMG_SIZE // 4) * (IMG_SIZE // 4))
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

def predict_image(model, image_path, device, transform):
    """Loads an image, preprocesses it, and makes a multi-class prediction."""
    model.eval()
    image = Image.open(image_path).convert('L')
    image_tensor = transform(image).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(image_tensor)
        probabilities = F.softmax(outputs, dim=1)
        confidence, predicted_idx = torch.max(probabilities, 1)
        
    return predicted_idx.item(), confidence.item(), image

def main():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(DATA_DIR):
        print("Error: Model or data not found. Please run 'prepare_dataset.py' and 'train.py' first.")
        return

    try:
        train_dir = os.path.join(DATA_DIR, 'train')
        class_names = sorted([d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d))])
        num_classes = len(class_names)
        if num_classes == 0: raise FileNotFoundError
        print(f"Found {num_classes} classes: {class_names}")
    except FileNotFoundError:
        print(f"Error: Could not determine classes from '{train_dir}'. Is the directory structure correct?")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ModeCNN(num_classes=num_classes).to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    print(f"Model '{MODEL_PATH}' loaded successfully on {device}.")

    transform = transforms.Compose([
        transforms.Grayscale(num_output_channels=1),
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])
    
    test_dir = os.path.join(DATA_DIR, 'test')
    all_test_images = []
    for cls_name in class_names:
        cls_dir = os.path.join(test_dir, cls_name)
        all_test_images.extend([os.path.join(cls_dir, f) for f in os.listdir(cls_dir)])
            
    random_samples = random.sample(all_test_images, min(NUM_PREDICTIONS, len(all_test_images)))
    
    print(f"\n--- Making Predictions on {len(random_samples)} Random Test Images ---")
    
    plt.figure(figsize=(15, 5))
    for i, image_path in enumerate(random_samples):
        pred_idx, confidence, image = predict_image(model, image_path, device, transform)
        
        true_label_str = os.path.basename(os.path.dirname(image_path))
        pred_label_str = class_names[pred_idx]
        
        plt.subplot(1, NUM_PREDICTIONS, i + 1)
        plt.imshow(image, cmap='gray')
        plt.title(f"True: {true_label_str}\nPred: {pred_label_str} ({confidence:.2f})",
                  color=("green" if true_label_str == pred_label_str else "red"))
        plt.axis('off')
        
    plt.tight_layout()
    plt.savefig('predictions_multiclass.png')
    plt.show()

if __name__ == '__main__':
    main()

