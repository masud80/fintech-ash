from firebase_functions import https_fn
import firebase_admin
from firebase_admin import credentials, auth, firestore
import json

# Initialize the Firebase Admin SDK only once
firebase_admin.initialize_app()

# CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://fintech-ash-80b97.web.app",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600"
}

@https_fn.on_request()
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
        result = {
            "financial_metrics": {"P/E Ratio": "18.2", "EPS": "3.70"},
            "analysis_summary": f"Analysis for stock {ticker} looks promising."
        }

        # Store in Firestore
        db.collection("previous_analysis").add({
            "user_id": uid,
            "ticker": ticker,
            "result": result,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

        return https_fn.Response(
            json.dumps(result),
            status=200,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )
