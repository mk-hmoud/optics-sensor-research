import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import os
from flask import Flask, request, jsonify

# --- Configuration ---
IMG_SIZE = 64
CLASS_NAMES = ['fundamental', 'higher', 'lower']
MODEL_PATH = 'mode_cnn_model.pth'

class ModeCNN(nn.Module):
    def __init__(self, num_classes):
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

print("Loading model and setting up server...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
num_classes = len(CLASS_NAMES)
model = ModeCNN(num_classes=num_classes).to(device)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.eval() # evaluation mode
print(f"Model '{MODEL_PATH}' loaded successfully on {device}.")

transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,))
])

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    """API endpoint to handle prediction requests."""
    data = request.get_json()
    if not data or 'image_dir' not in data:
        return jsonify({"error": "Missing 'image_dir' in request body"}), 400

    image_dir = data['image_dir']
    if not os.path.isdir(image_dir):
        return jsonify({"error": f"Directory not found: {image_dir}"}), 400

    results = []
    image_files = sorted([f for f in os.listdir(image_dir) if f.endswith('.png')])

    for image_name in image_files:
        image_path = os.path.join(image_dir, image_name)
        try:
            image = Image.open(image_path).convert('L')
            image_tensor = transform(image).unsqueeze(0).to(device)
            with torch.no_grad():
                outputs = model(image_tensor)
                probabilities = F.softmax(outputs, dim=1)
                confidence, predicted_idx = torch.max(probabilities, 1)
            
            pred_label = CLASS_NAMES[predicted_idx.item()]
            results.append({
                "file": image_name,
                "prediction": pred_label,
                "confidence": confidence.item()
            })
        except Exception as e:
            results.append({"file": image_name, "error": str(e)})
            
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)