from firebase_functions import https_fn
import logging
import json
from firebase_functions.options import MemoryOption
from financial_analysis import analyze_stock
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from datetime import datetime, timedelta
import concurrent.futures
from firebase.config import app, db, auth
from google.cloud import firestore

# Configure logging
logger = logging.getLogger('fintech')
logger.setLevel(logging.INFO)

# CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://fintech-ash-80b97.web.app",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "3600"
}

# Create a thread pool executor for running the analysis
executor = ThreadPoolExecutor(max_workers=1)

# Constants for timeouts
FUNCTION_TIMEOUT = 540  # 9 minutes (matching the http function timeout)
ANALYSIS_TIMEOUT = FUNCTION_TIMEOUT - 30  # Leave 30 seconds buffer for cleanup

def process_analysis_result(result: Any, doc_id: str) -> dict:
    """Process the analysis result and store it in Firestore"""
    try:
        def process_value(value):
            if isinstance(value, (int, float, bool)):
                return value
            elif isinstance(value, str):
                # Try to parse string as JSON if it looks like JSON
                if value.strip().startswith('{') or value.strip().startswith('['):
                    try:
                        import json
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return value
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif hasattr(value, 'raw'):
                return process_value(value.raw)
            else:
                return str(value)

        def process_analysis_component(component):
            """Special handling for analysis components that might be stringified JSON"""
            if isinstance(component, str):
                try:
                    import json
                    return json.loads(component)
                except json.JSONDecodeError:
                    return component
            elif isinstance(component, dict):
                return {k: process_value(v) for k, v in component.items()}
            return component

        if isinstance(result, dict):
            processed_result = {}
            
            # Handle the analysis section specially
            if 'analysis' in result:
                analysis_data = {}
                for key, value in result['analysis'].items():
                    # Process each analysis component
                    processed_value = process_analysis_component(value)
                    analysis_data[key] = processed_value
                processed_result['analysis'] = analysis_data
            
            # Handle other sections
            for key, value in result.items():
                if key != 'analysis':
                    processed_result[key] = process_value(value)
            
            return processed_result
        
        # Handle other types of results
        if isinstance(result, str):
            return {"analysis_summary": result}
        if isinstance(result, list):
            return {"analysis_summary": [process_value(item) for item in result]}
        
        return {"analysis_summary": str(result)}
        
    except Exception as e:
        logger.error(f"Error processing analysis result: {str(e)}")
        return {"error": str(e)}
    



def analysis_callback(future, doc_id: str, ticker: str) -> None:
    """Callback function to handle the analysis result"""

    try:
        # Get the result from the future
        
        try:
            # Set timeout slightly less than the function timeout to allow for cleanup
            result = future.result(timeout=ANALYSIS_TIMEOUT)
        except Exception as future_error:
            error_msg = f"Analysis failed: {str(future_error)}"
            logger.error(f"Analysis failed for ticker {ticker}: {error_msg}")
            update_firestore_error(doc_id, error_msg, ticker)
            return
            
        if not future.done():                
            error_msg = "Analysis incomplete - process did not complete"
            logger.error(f"Analysis incomplete for ticker {ticker}")
            update_firestore_error(doc_id, error_msg, ticker)
            return
            
        if result is None:            
            error_msg = "Analysis returned no results - check API connections and data availability"
            logger.error(f"No results returned for ticker {ticker}")
            update_firestore_error(doc_id, error_msg, ticker)
            return

        try:
            # Store in Firestore           
            analysis_ref = db.collection("analysis_results").document(doc_id)
            analysis_ref.set({
                "ticker": ticker,
                "result": result,  # result is already in the correct format from analyze_stock
                "status": "completed",
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Successfully stored result in Firestore for doc_id: {doc_id}")
        except Exception as process_error:
            error_msg = f"Error processing or storing result: {str(process_error)}"
            logger.error(f"Error storing results for ticker {ticker}: {error_msg}")
            update_firestore_error(doc_id, error_msg, ticker)
            
    except Exception as e:
        error_msg = f"Unexpected error in analysis: {str(e)}"
        logger.error(f"Unexpected error for ticker {ticker}: {error_msg}")
        update_firestore_error(doc_id, error_msg, ticker)

def update_firestore_error(doc_id: str, error_message: str, ticker: str) -> None:
    """Helper function to update Firestore with error status"""
    try:
      
        analysis_ref = db.collection("analysis_results").document(doc_id)
        analysis_ref.set({
            "ticker": ticker,
            "status": "error",
            "error_message": error_message,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as store_error:
        logger.error(f"Failed to store error in Firestore: {store_error}")


def check_existing_analysis(ticker: str) -> tuple[bool, dict | None]:
    """
    Check for existing analysis results for a given ticker.
    Returns a tuple of (should_proceed, response_data).
    If should_proceed is False, response_data contains the response to return.
    """
    try:
        # Query for any analysis of this ticker
        analysis_query = db.collection("analysis_results").where("ticker", "==", ticker).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1)
        docs = analysis_query.get()
        
        if not docs:
            return True, None
            
        doc = docs[0]  # Get the most recent analysis
        data = doc.to_dict()
        status = data.get("status")
 
        if status == "in_progress":
            return False, {
                "message": "Analysis already in progress",
                "status": status,
                "ticker": ticker,
                "document_id": doc.id
            }
        
        if status == "completed":
            timestamp = data.get("timestamp")
            if timestamp:
                # Convert Firestore timestamp to naive datetime
                if isinstance(timestamp, datetime):
                    doc_timestamp = timestamp.replace(tzinfo=None)
                else:
                    doc_timestamp = timestamp.datetime.replace(tzinfo=None)
                
                # Check if analysis is less than 24 hours old
                if datetime.now() - doc_timestamp < timedelta(hours=24):
                    return False, {
                        "message": "Retrieved existing analysis",
                        "status": status,
                        "ticker": ticker,
                        "result": data.get("result", {}),
                        "timestamp": doc_timestamp.isoformat()
                    }
        
        # If status is error or completed analysis is too old, proceed with new analysis
        return True, None
        
    except Exception as check_error:
        logger.error(f"Error checking existing analysis: {check_error}")
        return True, None



@https_fn.on_request(memory=MemoryOption.GB_1, timeout_sec=540, secrets=["SERPER_API_KEY", "OPENAI_API_KEY", "ALPHA_VANTAGE_API_KEY", "CLAUDE_API_KEY"])
def analyze_stock_endpoint(req: https_fn.Request) -> https_fn.Response:
    logger.info("Received request to analyze_stock_endpoint")
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
            logger.error("Unauthorized request - missing or invalid auth header")
            return https_fn.Response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )
        
        id_token = auth_header.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token["uid"]
        logger.info(f"Authenticated user: {uid}")

        body = req.get_json(silent=True)
        ticker = body.get("ticker") if body else None
        logger.info(f"Analyzing ticker: {ticker}")
        
        if not ticker:
            logger.error("Missing ticker in request")
            return https_fn.Response(
                json.dumps({"error": "Ticker is required"}),
                status=400,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )

        # Check for existing analysis results
        should_proceed, response_data = check_existing_analysis(ticker)
        
        if not should_proceed:
            logger.info(f"Using existing analysis for ticker: {ticker}")
            status_code = 202 if response_data["status"] == "in_progress" else 200
            return https_fn.Response(
                json.dumps(response_data),
                status=status_code,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )

        # Create initial Firestore document
        try:
            logger.info(f"Starting new analysis for ticker: {ticker}")
            # Create a new document with auto-generated ID
            analysis_ref = db.collection("analysis_results").document()
            doc_id = analysis_ref.id  # Get the ID before setting the document
            
            # Set the initial document data
            analysis_ref.set({
                "ticker": ticker,
                "status": "in_progress",
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Created Firestore document with ID: {doc_id}")
            
            # Submit the analysis task with a callback
            logger.info(f"Submitting analysis task for uid: {uid}")
            try:
                future = executor.submit(analyze_stock, ticker)
                future.add_done_callback(lambda f: analysis_callback(f, doc_id, ticker))
                logger.info("Analysis task submitted successfully")
            except Exception as submit_error:
                logger.error(f"Error submitting analysis task: {str(submit_error)}")
                raise submit_error
            
            # Return immediate response indicating analysis is in progress
            return https_fn.Response(
                json.dumps({
                    "message": "Analysis started",
                    "status": "in_progress",
                    "ticker": ticker,
                    "document_id": doc_id
                }),
                status=202,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )
            
        except Exception as store_error:
            logger.error(f"Error creating initial Firestore document: {store_error}")
            return https_fn.Response(
                json.dumps({"error": "Failed to start analysis"}),
                status=500,
                headers={**CORS_HEADERS, "Content-Type": "application/json"}
            )

    except Exception as e:
        logger.error(f"Error in analyze_stock_endpoint: {str(e)}")
        return https_fn.Response(
            json.dumps({"error": "An error occurred during analysis. Please try again."}),
            status=500,
            headers={**CORS_HEADERS, "Content-Type": "application/json"}
        )
