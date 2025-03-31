# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`



# initialize_app()
#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")

# Welcome to Cloud Functions for Firebase for Python!
# To get started, simply uncomment the below code or create your own.
# Deploy with `firebase deploy`

from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore, credentials
import json
from financial_analysis import analyze_stock
import os
import functions_framework
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Initialize Firebase Admin with service account credentials
try:
    cred = credentials.Certificate('../serviceAccountKey.json')
    initialize_app(cred)
except ValueError:
    # App already initialized
    pass

db = firestore.client()

@functions_framework.http
def analyze_stock_endpoint(request):
    # Enable CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Accept'
        }
        return ('', 204, headers)

    # Handle the actual request
    try:
        # Get the request data
        request_json = request.get_json()
        ticker = request_json.get('ticker')

        if not ticker:
            return (json.dumps({'error': 'Please provide a ticker symbol'}), 400, {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            })

        # Analyze the stock
        result = analyze_stock(ticker)

        # Store in Firestore
        db.collection('stock_analysis').add({
            'ticker': ticker,
            'result': result,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return (json.dumps(result), 200, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        })

    except Exception as e:
        return (json.dumps({'error': str(e)}), 500, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        })

# This is for local testing
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")