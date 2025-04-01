from firebase_functions import https_fn
import firebase_admin
from firebase_admin import  auth, firestore
import json
from firebase_functions.options import MemoryOption
from financial_analysis import analyze_stock
# Initialize the Firebase Admin SDK only once
firebase_admin.initialize_app()

# CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://fintech-ash-80b97.web.app",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600"
}

@https_fn.on_request(memory=MemoryOption.GB_1)
def analyze_stock_endpoint(req: https_fn.Request) -> https_fn.Response:
    # Handle CORS preflight requests
    if req.method == "OPTIONS":
        return https_fn.Response(
            "",
            status=204,
            headers=CORS_HEADERS
        )

    try:
        # 🔐 Verify Firebase ID token from Authorization header
        auth_header = req.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return https_fn.Response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )
        
        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]

        # 🔁 Move Firestore client inside the handler
        db = firestore.client()

        # Parse and validate the incoming request
        body = req.get_json(silent=True)
        ticker = body.get("ticker") if body else None
        if not ticker:
            return https_fn.Response(
                json.dumps({"error": "Ticker is required"}),
                status=400,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )

        # 🔍 Replace with actual stock analysis logic
        result = analyze_stock(ticker)

        # Ensure result is in JSON format
        if isinstance(result, dict):
            # Handle nested CrewOutput objects
            response_data = {}
            for key, value in result.items():
                if hasattr(value, 'raw'):
                    response_data[key] = value.raw
                else:
                    response_data[key] = value
        else:
            # Handle direct CrewOutput object
            if hasattr(result, 'raw'):
                response_data = {"analysis_summary": result.raw}
            else:
                response_data = {"analysis_summary": str(result)}

        # Store in Firestore
        db.collection("previous_analysis").add({
            "user_id": uid,
            "ticker": ticker,
            "result": response_data,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

        return https_fn.Response(
            json.dumps(response_data),
            status=200,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )
