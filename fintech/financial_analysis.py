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
    Cached function to get stock info with retry logic
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Rate limit hit, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Error fetching stock info: {str(e)}")
                return None


def analyze_stock(stock_selection):
    """
    Analyze a stock using CrewAI agents
    """
    # Get stock data with retry logic
    """
    info = get_stock_info(stock_selection)
    if not info:
        raise Exception("Failed to fetch stock data after multiple attempts. Please try again later.")

    # Basic financial metrics with error handling
    financial_metrics = {
        'Current Price': f"${info.get('currentPrice', 'N/A')}",
        'Market Cap': f"${info.get('marketCap', 'N/A'):,.0f}",
        'P/E Ratio': f"{info.get('forwardPE', 'N/A')}",
        '52 Week High': f"${info.get('fiftyTwoWeekHigh', 'N/A')}",
        '52 Week Low': f"${info.get('fiftyTwoWeekLow', 'N/A')}",
        'Volume': f"{info.get('volume', 'N/A'):,.0f}"
    } 
    """

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
        max_tokens=1000,
        api_key=openai_api_key
    )

    scrape_tool = ScrapeWebsiteTool()
    search_tool = SerperDevTool(
        name="search",        
        description="Fetches search results from the web",
        n_results=10  # Set the number of results to fetch
    )

    data_analyst_agent = Agent(
        role="Data Analyst",
        goal="Monitor and analyze market data in real-time to identify trends and predict market movements.",
        backstory="Specializing in financial markets, this agent uses statistical modeling and machine learning to provide crucial insights.",
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
    data_analysis_task = Task(
        description=f"Continuously monitor and analyze market data for {stock_selection}. Use statistical modeling and machine learning to identify trends and predict market movements.",
        expected_output=f"Insights and alerts about significant market opportunities or threats for {stock_selection}.",
        agent=data_analyst_agent,
        context=[f"Analyzing market data for {stock_selection} to identify trends and opportunities."]
    )
    
    strategy_development_task = Task(
        description=f"Develop and refine trading strategies based on the insights from the Data Analyst and user-defined risk tolerance (Medium). Consider trading preferences (1 year).",
        expected_output=f"A set of potential trading strategies for {stock_selection} that align with the user's risk tolerance.",
        agent=trading_strategy_agent,
        context=[f"Developing trading strategies for {stock_selection} based on market analysis and risk parameters."]
    )

    execution_planning_task = Task(
        description=f"Analyze approved trading strategies to determine the best execution methods for {stock_selection}, considering current market conditions and optimal pricing.",
        expected_output=f"Detailed execution plans suggesting how and when to execute trades for {stock_selection}.",
        agent=execution_agent,
        context=[f"Planning optimal execution strategies for {stock_selection} trades."]
    )

    risk_assessment_task = Task(
        description=f"Evaluate the risks associated with the proposed trading strategies and execution plans for {stock_selection}. Provide a detailed analysis of potential risks and suggest mitigation strategies.",
        expected_output=f"A comprehensive risk analysis report detailing potential risks and mitigation recommendations for {stock_selection}.",
        agent=risk_management_agent,
        context=[f"Assessing risks and developing mitigation strategies for {stock_selection} trading activities."]
    )

    manager_llm = LLM(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=500,
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
        'news_impact_consideration': True
    }

    # Run crew analysis
    result = financial_trading_crew.kickoff(inputs=financial_trading_inputs)

    return {
        #'financial_metrics': financial_metrics,
        'analysis_summary': result
    } 