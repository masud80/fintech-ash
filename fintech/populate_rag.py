import os
import json
from datetime import datetime
from typing import List, Dict, Any
from firestore_vector_store import FirestoreVectorStore
from langchain_openai import OpenAIEmbeddings
import requests
from dotenv import load_dotenv
from utils import get_alpha_vantage_api_key, get_openai_api_key

load_dotenv()

def fetch_market_news(ticker: str) -> List[Dict[str, Any]]:
    """Fetch market news for a given ticker using Alpha Vantage"""
    api_key = get_alpha_vantage_api_key()
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if "feed" not in data:
            return []
        
        documents = []
        for item in data["feed"]:
            documents.append({
                "text": f"{item['title']}\n\n{item['summary']}",
                "source": item.get("source", "Alpha Vantage"),
                "date": item.get("time_published", datetime.now().strftime("%Y%m%d")),
                "type": "market_news"
            })
        
        return documents
    except Exception as e:
        print(f"Error fetching market news: {str(e)}")
        return []

def fetch_regulatory_documents(ticker: str) -> List[Dict[str, Any]]:
    """Fetch regulatory documents for a given ticker"""
    # This is a placeholder - in a real implementation, you would fetch from SEC EDGAR or similar
    # For now, we'll use some sample regulatory information
    sample_docs = [
        {
            "text": "SEC filing requirements for technology companies include quarterly reports (10-Q), annual reports (10-K), and current reports (8-K). Companies must disclose material events, financial statements, and risk factors.",
            "source": "SEC Regulations",
            "date": "20240301",
            "type": "regulatory"
        },
        {
            "text": "Recent changes in market regulations require enhanced disclosure of environmental, social, and governance (ESG) factors in financial reporting. Companies must provide detailed information about their sustainability initiatives and climate-related risks.",
            "source": "SEC Updates",
            "date": "20240215",
            "type": "regulatory"
        }
    ]
    return sample_docs

def fetch_historical_patterns(ticker: str) -> List[Dict[str, Any]]:
    """Fetch historical trading patterns for a given ticker"""
    # This is a placeholder - in a real implementation, you would fetch from a historical data source
    # For now, we'll use some sample patterns
    sample_patterns = [
        {
            "text": "Historical analysis shows that this stock tends to perform well during earnings season, with an average 5% increase in price following positive earnings surprises. The stock has shown consistent growth in the technology sector over the past 5 years.",
            "source": "Historical Analysis",
            "date": "20240301",
            "type": "historical_pattern"
        },
        {
            "text": "Technical analysis indicates that the stock has strong support at the 200-day moving average. Previous breakouts from this level have resulted in sustained upward trends lasting 3-6 months.",
            "source": "Technical Analysis",
            "date": "20240215",
            "type": "historical_pattern"
        }
    ]
    return sample_patterns

def fetch_company_specific_info(ticker: str) -> List[Dict[str, Any]]:
    """Fetch company-specific information for a given ticker"""
    api_key = get_alpha_vantage_api_key()
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if not data:
            return []
        
        # Format company overview into a document
        overview_text = f"""
        Company Overview:
        Name: {data.get('Name', 'N/A')}
        Sector: {data.get('Sector', 'N/A')}
        Industry: {data.get('Industry', 'N/A')}
        Description: {data.get('Description', 'N/A')}
        
        Key Metrics:
        Market Cap: {data.get('MarketCapitalization', 'N/A')}
        P/E Ratio: {data.get('PERatio', 'N/A')}
        Dividend Yield: {data.get('DividendYield', 'N/A')}
        Beta: {data.get('Beta', 'N/A')}
        
        Financial Performance:
        Revenue Growth: {data.get('RevenueGrowth', 'N/A')}
        Profit Margin: {data.get('ProfitMargin', 'N/A')}
        Return on Equity: {data.get('ReturnOnEquityTTM', 'N/A')}
        """
        
        return [{
            "text": overview_text,
            "source": "Alpha Vantage",
            "date": datetime.now().strftime("%Y%m%d"),
            "type": "company_info"
        }]
    except Exception as e:
        print(f"Error fetching company info: {str(e)}")
        return []

def populate_database(ticker: str):
    """Populate the Firestore vector database with various types of information for a given ticker"""
    print(f"Populating Firestore vector database for {ticker}...")
    
    # Initialize Firestore vector store and embedding model
    vector_store = FirestoreVectorStore(collection_name="financial_data")
    embedding_model = OpenAIEmbeddings(api_key=get_openai_api_key())
    
    # Fetch and add different types of documents
    documents = []
    
    # Market news
    print("Fetching market news...")
    documents.extend(fetch_market_news(ticker))
    
    # Regulatory documents
    print("Fetching regulatory documents...")
    documents.extend(fetch_regulatory_documents(ticker))
    
    # Historical patterns
    print("Fetching historical patterns...")
    documents.extend(fetch_historical_patterns(ticker))
    
    # Company-specific information
    print("Fetching company-specific information...")
    documents.extend(fetch_company_specific_info(ticker))
    
    # Generate embeddings for all documents
    print("Generating embeddings...")
    texts = [doc["text"] for doc in documents]
    embeddings = embedding_model.embed_documents(texts)
    
    # Add all documents to the vector store
    print(f"Adding {len(documents)} documents to the vector store...")
    vector_store.add_documents(documents, embeddings)
    
    print("Database population complete!")

if __name__ == "__main__":
    # Example usage
    tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOG", "AMZN", "META", "NFLX", "TSM", "WMT", "JNJ", "VZ", "IBM", "MMM", "PFE", "BA", "CAT", "CSCO", "TM", "V", "WBA", "DIS", "GS", "JPM", "MS", "NKE", "ORCL", "QCOM", "TXN", "WMT", "XOM", "BA", "CAT", "CSCO", "TM", "V", "WBA", "DIS", "GS", "JPM", "MS", "NKE", "ORCL", "QCOM", "TXN", "WMT", "XOM"]   # You can change this to any ticker
    for ticker in tickers:
        populate_database(ticker) 