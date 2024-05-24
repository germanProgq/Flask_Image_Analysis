from flask import Flask, render_template, request
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')  # Use the non-interactive Agg backend
import matplotlib.pyplot as plt
import base64
import os
import requests

app = Flask(__name__)

# Define the upload and static folders
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
app.config['SOLVED_FOLDER'] = STATIC_FOLDER
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

folders_cleared = False

def clear_folder(folder_path):
    """Clears the specified folder."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

def clear_folders():
    global folders_cleared
    if not folders_cleared:
        clear_folder(UPLOAD_FOLDER)
        clear_folder(STATIC_FOLDER)
        folders_cleared = True

# Image processing function
def process_image(image, period, function='sin'):
    img_array = np.array(image)
    if function == 'sin':
        processed_array = np.sin(2 * np.pi * period * img_array / 255.0)
    elif function == 'cos':
        processed_array = np.cos(2 * np.pi * period * img_array / 255.0)
    else:
        raise ValueError("Invalid function type. Use 'sin' or 'cos'.")

    processed_array = (processed_array - processed_array.min()) / (processed_array.max() - processed_array.min()) * 255
    processed_image = Image.fromarray(processed_array.astype('uint8'))
    return processed_image

# Helper function to get color distribution
def get_colors(image):
    img_array = np.array(image)
    if len(img_array.shape) == 2:  # Grayscale image
        color_distribution = np.bincount(img_array.flatten(), minlength=256)
    else:  # RGB image
        color_distribution = np.zeros(256, dtype=int)
        for channel in range(img_array.shape[2]):
            color_distribution += np.bincount(img_array[:, :, channel].flatten(), minlength=256)
    return color_distribution.tolist()

# Route for uploading image and processing
@app.route('/', methods=['GET', 'POST'])
def index():
    clear_folders()  # Ensure folders are cleared on first request
    if request.method == 'POST':
        # Verify reCAPTCHA response
        recaptcha_response = request.form['g-recaptcha-response']
        secret_key = '6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe'  # Replace with your actual reCAPTCHA secret key

        verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        params = {
            'secret': secret_key,
            'response': recaptcha_response
        }
        response = requests.post(verify_url, data=params)
        data = response.json()

        if not data['success']:
            return 'reCAPTCHA verification failed!'

        period = float(request.form['period'])
        function = request.form['function']
        image_file = request.files['image']
        
        # Save the uploaded image to the upload folder
        filename = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(filename)
        
        # Analyze the saved image
        image = Image.open(filename)
        processed_image = process_image(image, period, function)
        original_colors = get_colors(image)
        processed_colors = get_colors(processed_image)
        
        # Save the processed image
        processed_filename = os.path.join(app.config['SOLVED_FOLDER'], 'processed_image.png')
        processed_image.save(processed_filename)
        
        # Plot color distribution and save to file
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        axes[0].bar(range(len(original_colors)), original_colors, color='b')
        axes[0].set_title('Original Image Color Distribution')
        axes[1].bar(range(len(processed_colors)), processed_colors, color='r')
        axes[1].set_title('Processed Image Color Distribution')
        plt.tight_layout()
        plot_filename = os.path.join(app.config['SOLVED_FOLDER'], 'color_distribution_plot.png')
        plt.savefig(plot_filename)
        plt.close()

        # Read the plot file and encode it as base64
        with open(plot_filename, 'rb') as f:
            plot_data = base64.b64encode(f.read()).decode('utf-8')

        # Pass the plot data, processed image filename, and color distributions to the template
        return render_template('result.html', processed_image='processed_image.png', plot_data=plot_data, original_colors=original_colors, processed_colors=processed_colors, enumerate=enumerate)

    return render_template('index.html')

# Run the Flask application within the main thread
if __name__ == '__main__':
    app.run(debug=True)
