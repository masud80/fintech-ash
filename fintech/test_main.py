import pytest
from unittest.mock import patch, MagicMock
from firebase_functions import https_fn
from main import analyze_stock_endpoint
from financial_analysis import analyze_stock
import json

@pytest.fixture
def mock_request():
    request = MagicMock(spec=https_fn.Request)
    request.method = "POST"
    request.headers = {
        "Authorization": "Bearer mock_token",
        "Content-Type": "application/json"
    }
    request.get_json.return_value = {"ticker": "AAPL"}
    return request

@pytest.fixture
def mock_firebase_auth():
    with patch("main.auth") as mock_auth:
        mock_auth.verify_id_token.return_value = {"uid": "test_user_id"}
        yield mock_auth

@pytest.fixture
def mock_firestore():
    with patch("main.firestore") as mock_firestore:
        mock_client = MagicMock()
        mock_firestore.client.return_value = mock_client
        yield mock_client



def test_successful_analysis(mock_request, mock_firebase_auth, mock_firestore):
    response = analyze_stock_endpoint(mock_request)
    
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers
    assert json.loads(response.get_data(as_text=True)).get('analysis_summary') is not None
  

def test_missing_ticker(mock_request, mock_firebase_auth):
    mock_request.get_json.return_value = {}
    response = analyze_stock_endpoint(mock_request)
    
    assert response.status_code == 400
    assert json.loads(response.get_data(as_text=True)) == {"error": "Ticker is required"}

def test_missing_auth_header(mock_request):
    mock_request.headers = {}
    response = analyze_stock_endpoint(mock_request)
    
    assert response.status_code == 401
    assert json.loads(response.get_data(as_text=True)) == {"error": "Unauthorized"}

def test_cors_preflight():
    request = MagicMock(spec=https_fn.Request)
    request.method = "OPTIONS"
    response = analyze_stock_endpoint(request)
    
    assert response.status_code == 204
    assert "Access-Control-Allow-Origin" in response.headers 


