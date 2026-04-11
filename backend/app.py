import os
import sys
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app():
    app = Flask(__name__)

    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:4173",
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })

    from backend.api.chat import chat_bp
    app.register_blueprint(chat_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    print(f"\n  ForgeAI backend running → http://localhost:{port}\n")
    app.run(debug=True, port=port)
