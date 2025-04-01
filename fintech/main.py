from firebase_functions import https_fn
import firebase_admin
from firebase_admin import  auth, firestore
import json
from firebase_functions.options import MemoryOption
from financial_analysis import analyze_stock
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any
from firebase_functions import websocket_fn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Firebase Admin SDK only once
firebase_admin.initialize_app()

# CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://fintech-ash-80b97.web.app",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600"
}

# Create a thread pool executor for running the analysis
executor = ThreadPoolExecutor(max_workers=1)

# Store active WebSocket connections
active_connections = {}

def process_analysis_result(result: Any, uid: str, ticker: str) -> dict:
    """Process the analysis result and store it in Firestore"""
    # Convert result to JSON-serializable format
    if isinstance(result, dict):
        response_data = {}
        for key, value in result.items():
            if hasattr(value, 'raw'):
                response_data[key] = value.raw
            else:
                response_data[key] = str(value)  # Convert any non-serializable objects to strings
    else:
        if hasattr(result, 'raw'):
            response_data = {"analysis_summary": result.raw}
        else:
            response_data = {"analysis_summary": str(result)}

    # Store in Firestore
    try:
        db = firestore.client()
        db.collection("previous_analysis").add({
            "user_id": uid,
            "ticker": ticker,
            "result": response_data,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as store_error:
        logger.error(f"Error storing result in Firestore: {store_error}")
        # Continue even if storage fails
        pass

    return response_data

def analysis_callback(future, uid: str, ticker: str) -> None:
    """Callback function to handle the analysis result"""
    try:
        result = future.result()
        response_data = process_analysis_result(result, uid, ticker)
        
        # Send result to WebSocket if connection exists
        if uid in active_connections:
            try:
                active_connections[uid].send(json.dumps({
                    "type": "analysis_complete",
                    "data": response_data
                }))
            except Exception as ws_error:
                logger.error(f"Error sending WebSocket message: {ws_error}")
    except Exception as e:
        logger.error(f"Error in analysis callback: {str(e)}")
        if uid in active_connections:
            try:
                active_connections[uid].send(json.dumps({
                    "type": "error",
                    "message": "Analysis failed"
                }))
            except Exception as ws_error:
                logger.error(f"Error sending WebSocket error message: {ws_error}")

@websocket_fn.on_connect()
def on_connect(ws: websocket_fn.WebSocket) -> None:
    """Handle WebSocket connection"""
    try:
        # Get the user's ID from the connection
        uid = ws.auth.uid
        active_connections[uid] = ws
        logger.info(f"WebSocket connected for user {uid}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        ws.close()

@websocket_fn.on_disconnect()
def on_disconnect(ws: websocket_fn.WebSocket) -> None:
    """Handle WebSocket disconnection"""
    try:
        uid = ws.auth.uid
        if uid in active_connections:
            del active_connections[uid]
            logger.info(f"WebSocket disconnected for user {uid}")
    except Exception as e:
        logger.error(f"Error in WebSocket disconnection: {str(e)}")

@https_fn.on_request(memory=MemoryOption.GB_1, timeout_sec=540, secrets=["SERPER_API_KEY", "OPENAI_API_KEY"])
def analyze_stock_endpoint(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return https_fn.Response(
            "",
            status=204,
            headers=CORS_HEADERS
        )

    try:
        # Verify Firebase ID token
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

        body = req.get_json(silent=True)
        ticker = body.get("ticker") if body else None
        
        if not ticker:
            return https_fn.Response(
                json.dumps({"error": "Ticker is required"}),
                status=400,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )

        # Submit the analysis task with a callback
        future = executor.submit(analyze_stock, ticker)
        future.add_done_callback(lambda f: analysis_callback(f, uid, ticker))

        # Return immediate response indicating analysis is in progress
        return https_fn.Response(
            json.dumps({"message": "Analysis started", "ticker": ticker}),
            status=202,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )

    except Exception as e:
        logger.error(f"Error in analyze_stock_endpoint: {str(e)}")
        return https_fn.Response(
            json.dumps({"error": "An error occurred during analysis. Please try again."}),
            status=500,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )
