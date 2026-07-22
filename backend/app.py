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
                # Local development
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:4173",
                # Vercel production
                "https://forge-ai-jet.vercel.app",
                # Vercel preview deployments
                "https://forge-ai-jet-jehanfernando02.vercel.app",
            ],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })

    from backend.api.chat import chat_bp
    app.register_blueprint(chat_bp)

    return app


app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    print(f"\n  ForgeAI backend running → http://0.0.0.0:{port}\n")
    app.run(debug=True, host='0.0.0.0', port=port)


