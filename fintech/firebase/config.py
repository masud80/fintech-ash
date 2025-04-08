import firebase_admin
from firebase_admin import firestore, storage, credentials, auth
import os

def get_app():
    """Get or initialize Firebase Admin app"""
    try:
        # Try to get the default app first
        return firebase_admin.get_app()
    except ValueError:
        # If no app exists, initialize one
        if os.getenv('FUNCTION_TARGET'):
            # In Firebase Functions, use the default app
            return firebase_admin.initialize_app()
        else:
            # For local development, use service account credentials
            # Path to serviceAccountKey.json is relative to this file's location
            cred = credentials.Certificate(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'serviceAccountKey.json'))
            return firebase_admin.initialize_app(cred)

# Initialize Firebase app and services
try:
    app = get_app()
    db = firestore.client(app)
    
    # Initialize Storage (if available)
    try:
        bucket = storage.bucket(app)
    except Exception as e:
        print(f"Warning: Could not initialize Firebase Storage: {str(e)}")
        bucket = None
        
except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    raise

# Firebase configuration
config = {
    'app': {
        'apiKey': "AIzaSyDTVrNzD-YYFnvqakAk1LysPe8jPrpyScc",
        'authDomain': "fintech-ash-80b97.firebaseapp.com",
        'projectId': "fintech-ash-80b97",
        'storageBucket': "fintech-ash-80b97.firebasestorage.app",
        'messagingSenderId': "972685478512",
        'appId': "1:972685478512:web:34d1aa305be183112702b5",
        'measurementId': "G-FHFL400HD3"
    }
}

# Export the Firebase services and config
__all__ = ['app', 'db', 'storage', 'config', 'auth'] 