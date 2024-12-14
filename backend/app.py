import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS # type: ignore
from flask import Flask, request, jsonify
import tensorflow as tf
from PIL import Image
import numpy as np
from flask import send_from_directory



app = Flask(__name__,static_folder='static')
app.secret_key = "your_secret_key"
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

init_db()

try:
    model = tf.keras.models.load_model('alzheimers_model.h5')
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")

class_labels = {
    0: "MildDemented",
    1: "VeryMildDemented",
    2: "ModerateDemented",
    3: "NonDemented"
}


def preprocess_image(image_path):
    """Preprocess the image for prediction."""
    image = Image.open(image_path)
    image = image.resize((224, 224))  # Adjust size to model's input shape
    image = np.array(image) / 255.0  # Normalize pixel values
    image = np.expand_dims(image, axis=0)  # Add batch dimension
    return image

#Routes
@app.route('/favicon.ico') 
def favicon(): 
    try: return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon') 
    except Exception as e:
         app.logger.error(f"Error occurred: {e}") 
    return jsonify({'error': 'Internal Server Error'}), 500
@app.route("/")
def index():
    # If user is logged in, redirect to detection page
    if "username" in session:
        return redirect(url_for("detection"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check credentials
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["username"] = username  # Store username in session
            return redirect(url_for("detection"))
        else:
            flash("Invalid username or password.")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        try:
            # Add user to database
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash("Signup successful! Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists. Please choose a different one.")
            return redirect(url_for("signup"))

    return render_template("signup.html")

@app.route("/detection", methods=["GET", "POST"])
def detection():
    # If user is not logged in, redirect to login page
    if "username" not in session:
        flash("Please log in to access the detection page.")
        return redirect(url_for("login"))

    if request.method == "POST":
        # Handle file upload here
        file = request.files.get("file")
        if not file:
            flash("Please upload an image file.")
        else:
            flash("File uploaded successfully (processing logic not implemented).")
        return redirect(url_for("detection"))

    return render_template("detection.html", username=session["username"])

@app.route('/predict', methods=['POST'])
def predict_image():
    try:
        file = request.files['file']
        if not file:
            return jsonify({"error": "No file provided"}), 400

        # Process the image
        img = Image.open(file.stream).convert('RGB')
        img = img.resize((224, 224))  # Resize according to your model input
        img_array = np.array(img) / 255.0  # Normalize image
        img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension

        # Make prediction
        prediction = model.predict(img_array)

        # Get the predicted class index
        predicted_class_index = np.argmax(prediction, axis=1)[0]
        
        # Get the human-readable label
        prediction_label = class_labels.get(predicted_class_index, "Unknown")
        
        return jsonify({"prediction": prediction_label})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/logout")
def logout():
    session.pop("username", None)  # Remove username from session
    flash("You have been logged out.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
