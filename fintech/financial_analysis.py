import yfinance as yf
import pandas as pd
from crewai import Agent, Task, Crew, LLM, Process
from dotenv import load_dotenv
from crewai_tools import ScrapeWebsiteTool, SerperDevTool
import os
from utils import get_openai_api_key, get_serper_api_key
import time
from functools import lru_cache
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



@lru_cache(maxsize=100)
def get_stock_info(ticker):
    """
    Cached function to get comprehensive stock info with retry logic
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get historical data for technical analysis
            hist = stock.history(period="1y")
            
            # Calculate additional metrics
            if not hist.empty:
                sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
                sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
                rsi = calculate_rsi(hist['Close'])
                volatility = hist['Close'].pct_change().std() * (252 ** 0.5)  # Annualized volatility
            else:
                sma_50 = sma_200 = rsi = volatility = None
            
            # Combine basic info with technical indicators
            enhanced_info = {
                # Basic Info
                'currentPrice': info.get('currentPrice'),
                'marketCap': info.get('marketCap'),
                'forwardPE': info.get('forwardPE'),
                'trailingPE': info.get('trailingPE'),
                'dividendYield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
                'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
                'volume': info.get('volume'),
                'averageVolume': info.get('averageVolume'),
                
                # Financial Metrics
                'returnOnEquity': info.get('returnOnEquity'),
                'profitMargins': info.get('profitMargins'),
                'revenueGrowth': info.get('revenueGrowth'),
                'debtToEquity': info.get('debtToEquity'),
                'quickRatio': info.get('quickRatio'),
                'currentRatio': info.get('currentRatio'),
                
                # Technical Indicators
                'SMA50': sma_50,
                'SMA200': sma_200,
                'RSI': rsi,
                'annualizedVolatility': volatility,
                
                # Additional Data
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'fullTimeEmployees': info.get('fullTimeEmployees'),
                'recommendationKey': info.get('recommendationKey')
            }
            
            return enhanced_info
            
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Rate limit hit, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Error fetching stock info: {str(e)}")
                return None

def calculate_rsi(prices, periods=14):
    """Calculate RSI technical indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def analyze_stock(stock_selection):
    """
    Analyze a stock using CrewAI agents
    """
    # Get stock data with retry logic
    stock_data = get_stock_info(stock_selection)
    if not stock_data:
        raise Exception("Failed to fetch stock data after multiple attempts. Please try again later.")
    
    openai_api_key = get_openai_api_key()
    serper_api_key = get_serper_api_key()

    # Only set environment variables if they're not already set
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = openai_api_key
    if not os.getenv("OPENAI_MODEL"):
        os.environ["OPENAI_MODEL"] = 'gpt-4o-mini'
    if not os.getenv("SERPER_API_KEY"):
        os.environ["SERPER_API_KEY"] = serper_api_key

    llm = LLM(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=4000,
        api_key=openai_api_key
    )

    scrape_tool = ScrapeWebsiteTool()
    search_tool = SerperDevTool(
        name="search",        
        description="Fetches search results from the web",
        n_results=10  # Set the number of results to fetch
    )

    data_analyst_agent = Agent(
        role="Quantitative Data Analyst",
        goal="Analyze comprehensive market data including technical indicators, financial metrics, and market trends to provide data-driven insights.",
        backstory="Expert in quantitative analysis with deep knowledge of technical indicators, financial ratios, and statistical modeling. Specializes in combining multiple data points to form actionable insights.",
        verbose=True,
        allow_delegation=True,
        llm=llm,
        tools=[scrape_tool, search_tool]
    )
    
    trading_strategy_agent = Agent(
        role="Trading Strategy Developer",
        goal="Develop and test various trading strategies based on insights from the Data Analyst Agent.",
        backstory="Equipped with a deep understanding of financial markets and quantitative analysis.",
        verbose=True,
        allow_delegation=True,
        llm=llm,
        tools=[scrape_tool, search_tool]
    )
    
    execution_agent = Agent(
        role="Trade Advisor",
        goal="Suggest optimal trade execution strategies based on approved trading strategies.",
        backstory="This agent specializes in analyzing the timing, price, and logistical details of potential trades.",
        verbose=True,
        allow_delegation=True,
        llm=llm,
        tools=[scrape_tool, search_tool]
    )
    
    risk_management_agent = Agent(
        role="Risk Advisor",
        goal="Evaluate and provide insights on the risks associated with potential trading activities.",
        backstory="Armed with a deep understanding of risk assessment models and market dynamics.",
        verbose=True,
        allow_delegation=True,
        llm=llm,
        tools=[scrape_tool, search_tool]
    )

    # Create tasks with proper string formatting
    logger.info(f"Creating data analysis task for {stock_selection}")
    try:
        data_analysis_task = Task(
            description=f"""
            Perform comprehensive quantitative analysis for {stock_selection}:
            1. Analyze fundamental metrics (P/E, P/B, profit margins, ROE)
            2. Evaluate technical indicators (SMA50/200, RSI, volatility)
            3. Compare key ratios to industry averages
            4. Assess market sentiment and institutional recommendations
            5. Identify key risk metrics (beta, debt ratios)
            
            Use the get_stock_info function to access real-time market data and provide specific numerical insights in your analysis.
            """,
            expected_output=f"Detailed quantitative analysis report for {stock_selection} including specific metrics, their interpretations, and comparative analysis.",
            agent=data_analyst_agent
        )
        logger.info("Data analysis task created successfully")
    except Exception as e:
        logger.error(f"Error creating data analysis task: {str(e)}")
        raise
    
    logger.info(f"Creating strategy development task for {stock_selection}")
    try:
        strategy_development_task = Task(
            description=f"Develop and refine trading strategies based on the insights from the Data Analyst and user-defined risk tolerance (Medium). Consider trading preferences (1 year).",
            expected_output=f"A set of potential trading strategies for {stock_selection} that align with the user's risk tolerance.",
            agent=trading_strategy_agent
        )
        logger.info("Strategy development task created successfully")
    except Exception as e:
        logger.error(f"Error creating strategy development task: {str(e)}")
        raise
    
    logger.info(f"Creating execution planning task for {stock_selection}")
    try:
        execution_planning_task = Task(
            description=f"Analyze approved trading strategies to determine the best execution methods for {stock_selection}, considering current market conditions and optimal pricing.",
            expected_output=f"Detailed execution plans suggesting how and when to execute trades for {stock_selection}.",
            agent=execution_agent
        )
        logger.info("Execution planning task created successfully")
    except Exception as e:
        logger.error(f"Error creating execution planning task: {str(e)}")
        raise
    
    logger.info(f"Creating risk assessment task for {stock_selection}")
    try:
        risk_assessment_task = Task(
            description=f"Evaluate the risks associated with the proposed trading strategies and execution plans for {stock_selection}. Provide a detailed analysis of potential risks and suggest mitigation strategies.",
            expected_output=f"A comprehensive risk analysis report detailing potential risks and mitigation recommendations for {stock_selection}.",
            agent=risk_management_agent
        )
        logger.info("Risk assessment task created successfully")
    except Exception as e:
        logger.error(f"Error creating risk assessment task: {str(e)}")
        raise

    manager_llm = LLM(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=4000,
        api_key=openai_api_key
    )

    financial_trading_crew = Crew(
        agents=[data_analyst_agent,
                trading_strategy_agent,
                execution_agent,
                risk_management_agent],
        tasks=[data_analysis_task,
               strategy_development_task,
               execution_planning_task,
               risk_assessment_task],
        manager_llm=manager_llm,
        process=Process.hierarchical,
        verbose=True
    )

    financial_trading_inputs = {
        'stock_selection': stock_selection,
        'initial_capital': '100000',
        'risk_tolerance': 'Medium',
        'trading_strategy_preference': '1 year',
        'news_impact_consideration': True,
        'stock_data': stock_data  # Make quantitative data available to agents
    }

    # Run crew analysis
    result = financial_trading_crew.kickoff(inputs=financial_trading_inputs)

    # Combine quantitative data with analysis
    final_result = {
        'quantitative_data': {
            'Current Price': f"${stock_data.get('currentPrice', 'N/A')}",
            'Market Cap': f"${stock_data.get('marketCap', 'N/A'):,.0f}" if stock_data.get('marketCap') else 'N/A',
            'Forward P/E': f"{stock_data.get('forwardPE', 'N/A')}",
            'RSI': f"{stock_data.get('RSI', 'N/A'):.2f}" if stock_data.get('RSI') else 'N/A',
            'SMA50': f"${stock_data.get('SMA50', 'N/A'):.2f}" if stock_data.get('SMA50') else 'N/A',
            'SMA200': f"${stock_data.get('SMA200', 'N/A'):.2f}" if stock_data.get('SMA200') else 'N/A',
            'Beta': f"{stock_data.get('beta', 'N/A')}",
            'Volatility': f"{stock_data.get('annualizedVolatility', 'N/A'):.2%}" if stock_data.get('annualizedVolatility') else 'N/A',
            'Return on Equity': f"{stock_data.get('returnOnEquity', 'N/A'):.2%}" if stock_data.get('returnOnEquity') else 'N/A',
            'Profit Margins': f"{stock_data.get('profitMargins', 'N/A'):.2%}" if stock_data.get('profitMargins') else 'N/A'
        }
    }

    # Ensure result is a dictionary with analysis_summary key
    if isinstance(result, str):
        final_result['analysis_summary'] = result
    elif isinstance(result, dict):
        final_result['analysis_summary'] = result.get('analysis_summary', result)
    else:
        final_result['analysis_summary'] = str(result)

    return final_result 