from app import app
import flask_app  # Import the flask_app module to register its routes with the app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
