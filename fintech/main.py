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

# Initialize Firebase Admin with service account credentials
try:
    cred = credentials.Certificate('../serviceAccountKey.json')
    initialize_app(cred)
except ValueError:
    # App already initialized
    pass

db = firestore.client()

@https_fn.on_request()
def analyze_stock_endpoint(req: https_fn.Request) -> https_fn.Response:
    # Enable CORS
    if req.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Accept'
        }
        return https_fn.Response('', status=204, headers=headers)

    # Handle the actual request
    try:
        # Get the request data
        request_json = req.get_json()
        ticker = request_json.get('ticker')

        if not ticker:
            return https_fn.Response(
                json.dumps({'error': 'Please provide a ticker symbol'}),
                status=400,
                headers={
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            )

        # Analyze the stock
        result = analyze_stock(ticker)

        # Store in Firestore
        db.collection('stock_analysis').add({
            'ticker': ticker,
            'result': result,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return https_fn.Response(
            json.dumps(result),
            status=200,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        )

    except Exception as e:
        return https_fn.Response(
            json.dumps({'error': str(e)}),
            status=500,
            headers={
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        )

#
#
# @https_fn.on_request()
# def on_request_example(req: https_fn.Request) -> https_fn.Response:
#     return https_fn.Response("Hello world!")