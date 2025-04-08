import yfinance as yf
import pandas as pd
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import os
from utils import get_claude_api_key, get_alpha_vantage_api_key
import time
from functools import lru_cache
import logging
import requests
from datetime import datetime, timedelta
from rag_utils import rag_manager

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the state for our graph
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    stock_data: dict
    analysis_results: dict
    current_agent: str

def safe_float_convert(value, default=0.0):
    """
    Safely convert a value to float, handling 'None' strings and other edge cases
    """
    if value is None or value == 'None' or value == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

@lru_cache(maxsize=100)
def get_stock_info(ticker):
    """
    Cached function to get comprehensive stock info using Alpha Vantage API
    """
    max_retries = 3
    retry_delay = 5  # seconds
    api_key = get_alpha_vantage_api_key()
    
    for attempt in range(max_retries):
        try:
            # Get daily time series data
            daily_url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}"
            daily_response = requests.get(daily_url)
            daily_data = daily_response.json()
            
            logger.info(f"Daily data response for {ticker}: {daily_data.keys()}")
            
            # Get company overview
            overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
            overview_response = requests.get(overview_url)
            overview_data = overview_response.json()
            
            if "Error Message" in daily_data or "Error Message" in overview_data:
                raise Exception("API Error: " + (daily_data.get("Error Message") or overview_data.get("Error Message")))
            
            # Extract daily data
            daily_series = daily_data.get("Time Series (Daily)", {})
            
            # Check if we have any data
            if not daily_series:
                logger.error(f"No daily data available for ticker {ticker}")
                return None
                
            logger.info(f"Number of daily data points for {ticker}: {len(daily_series)}")
            
            try:
                latest_date = max(daily_series.keys())
                latest_data = daily_series[latest_date]
                logger.info(f"Latest date for {ticker}: {latest_date}")
            except (ValueError, KeyError) as e:
                logger.error(f"Error processing daily data for {ticker}: {str(e)}")
                return None
            
            # Convert daily data to DataFrame for technical analysis
            try:
                df = pd.DataFrame.from_dict(daily_series, orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.astype(float)
                logger.info(f"DataFrame shape for {ticker}: {df.shape}")
            except Exception as e:
                logger.error(f"Error converting data to DataFrame for {ticker}: {str(e)}")
                df = pd.DataFrame()  # Empty DataFrame as fallback
            
            # Calculate technical indicators
            if not df.empty:
                try:
                    sma_50 = df['4. close'].rolling(window=50).mean().iloc[-1]
                    sma_200 = df['4. close'].rolling(window=200).mean().iloc[-1]
                    logger.info(f"Calculated SMAs for {ticker} - SMA50: {sma_50}, SMA200: {sma_200}")
                    rsi = calculate_rsi(df['4. close'])
                    volatility = df['4. close'].pct_change().std() * (252 ** 0.5)  # Annualized volatility
                except Exception as e:
                    logger.warning(f"Error calculating technical indicators for {ticker}: {str(e)}")
                    sma_50 = sma_200 = rsi = volatility = None
            else:
                sma_50 = sma_200 = rsi = volatility = None
            
            # Combine data from both endpoints using safe float conversion
            enhanced_info = {
                # Basic Info
                'currentPrice': safe_float_convert(latest_data.get('4. close')),
                'marketCap': safe_float_convert(overview_data.get('MarketCapitalization')),
                'forwardPE': safe_float_convert(overview_data.get('ForwardPE')),
                'trailingPE': safe_float_convert(overview_data.get('TrailingPE')),
                'dividendYield': safe_float_convert(overview_data.get('DividendYield')),
                'beta': safe_float_convert(overview_data.get('Beta')),
                'fiftyTwoWeekHigh': safe_float_convert(overview_data.get('52WeekHigh')),
                'fiftyTwoWeekLow': safe_float_convert(overview_data.get('52WeekLow')),
                'volume': safe_float_convert(latest_data.get('5. volume')),
                'averageVolume': safe_float_convert(overview_data.get('AverageVolume')),
                
                # Financial Metrics
                'returnOnEquity': safe_float_convert(overview_data.get('ReturnOnEquityTTM')),
                'profitMargins': safe_float_convert(overview_data.get('ProfitMargin')),
                'revenueGrowth': safe_float_convert(overview_data.get('RevenueGrowth')),
                'debtToEquity': safe_float_convert(overview_data.get('DebtToEquityRatio')),
                'quickRatio': safe_float_convert(overview_data.get('QuickRatio')),
                'currentRatio': safe_float_convert(overview_data.get('CurrentRatio')),
                
                # Technical Indicators
                'SMA50': sma_50,
                'SMA200': sma_200,
                'RSI': rsi,
                'annualizedVolatility': volatility,
                
                # Additional Data
                'sector': overview_data.get('Sector'),
                'industry': overview_data.get('Industry'),
                'fullTimeEmployees': int(safe_float_convert(overview_data.get('FullTimeEmployees'))),
                'recommendationKey': overview_data.get('AnalystTargetPrice')
            }
            
            return enhanced_info
            
        except Exception as e:
            if "API call frequency" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Rate limit hit, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Error fetching stock info for {ticker}: {str(e)}")
                return None

def calculate_rsi(prices, periods=14):
    """Calculate RSI technical indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def create_agent(name: str, description: str, llm: ChatAnthropic):
    """Create a LangChain agent with specific role and capabilities"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"You are a {name}. {description}"),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    chain = prompt | llm | JsonOutputParser()
    return chain

def analyze_stock(stock_selection: str):
    """
    Analyze a stock using LangGraph for multi-agent collaboration
    """
    try:
        # Get stock data with retry logic
        stock_data = get_stock_info(stock_selection)
        if not stock_data:
            raise Exception("Failed to fetch stock data after multiple attempts. Please check your Alpha Vantage API key and try again later.")
        
        claude_api_key = get_claude_api_key()
        if not claude_api_key:
            raise Exception("Claude API key not found. Please check your environment variables.")

        # Set up LLM
        llm = ChatAnthropic(
            model_name="claude-3-5-sonnet-latest",
            temperature=0.7,
            max_tokens_to_sample=4000,
            api_key=claude_api_key
        )

        # Create agents
        data_analyst = create_agent(
            "Data Analyst",
            "Expert in quantitative analysis with deep knowledge of technical indicators, financial ratios, and statistical modeling.",
            llm
        )
        
        trading_strategist = create_agent(
            "Trading Strategist",
            "Equipped with a deep understanding of financial markets and quantitative analysis.",
            llm
        )
        
        execution_agent = create_agent(
            "Trade Execution",
            "Specializes in analyzing the timing, price, and logistical details of potential trades.",
            llm
        )
        
        risk_manager = create_agent(
            "Risk Manager",
            "Armed with a deep understanding of risk assessment models and market dynamics.",
            llm
        )

        # Define the graph workflow
        workflow = StateGraph(AgentState)

        # Add nodes for each agent
        def data_analysis(state: AgentState):
            messages = state["messages"]
            stock_data = state["stock_data"]
            
            # Retrieve relevant context for data analysis
            context_query = f"Analyze {stock_selection} stock performance, financial metrics, and market position"
            relevant_docs = rag_manager.retrieve_relevant_context(context_query, "market_analysis")
            context = rag_manager.format_context_for_prompt(relevant_docs)
            
            analysis_prompt = f"""
            {context}
            
            Perform comprehensive quantitative analysis for {stock_selection} and provide your response in the following JSON format:
            {{
                "fundamental_metrics": {{
                    "pe_ratios": {{
                        "forward_pe": float,
                        "trailing_pe": float
                    }},
                    "price_range": {{
                        "week_52_high": float,
                        "week_52_low": float
                    }},
                    "market_cap": float,
                    "dividend_yield": float
                }},
                "technical_indicators": {{
                    "sma_50": float,
                    "sma_200": float,
                    "rsi": float,
                    "volatility": float
                }},
                "financial_metrics": {{
                    "return_on_equity": float,
                    "profit_margins": float,
                    "revenue_growth": float,
                    "debt_to_equity": float
                }},
                "risk_metrics": {{
                    "beta": float,
                    "current_ratio": float,
                    "quick_ratio": float
                }}
            }}

            Use the provided stock data to fill in the values. If any data is not available, use null.
            Stock Data: {stock_data}
            """
            
            messages.append(HumanMessage(content=analysis_prompt))
            response = data_analyst.invoke({"messages": messages})
            
            return {
                "messages": messages + [HumanMessage(content=str(response))],
                "analysis_results": {"data_analysis": response},
                "current_agent": "trading_strategist"
            }

        def trading_strategy(state: AgentState):
            messages = state["messages"]
            analysis = state["analysis_results"]["data_analysis"]
            
            # Retrieve relevant context for trading strategy
            context_query = f"Develop trading strategies for {stock_selection} based on current market conditions and historical patterns"
            relevant_docs = rag_manager.retrieve_relevant_context(context_query, "trading_strategy")
            context = rag_manager.format_context_for_prompt(relevant_docs)
            
            strategy_prompt = f"""
            {context}
            
            Develop trading strategies for {stock_selection} and provide ONLY the JSON response in the following format:
            {{
                "trading_strategy": {{
                    "technical_analysis": {{
                        "rsi": float,
                        "sma_50": float,
                        "volatility": float,
                        "current_price": float
                    }},
                    "entry_points": {{
                        "primary": {{
                            "price_range": string,
                            "conditions": string
                        }},
                        "secondary": {{
                            "price_target": float,
                            "conditions": string
                        }}
                    }},
                    "exit_points": {{
                        "profit_targets": {{
                            "initial": float,
                            "description": string
                        }},
                        "stop_loss": {{
                            "price": float,
                            "description": string
                        }},
                        "trailing_stop": {{
                            "percentage": float,
                            "description": string
                        }}
                    }},
                    "position_sizing": {{
                        "recommended_size": string,
                        "entry_breakdown": {{
                            "first_entry": {{
                                "percentage": float,
                                "conditions": string
                            }},
                            "second_entry": {{
                                "percentage": float,
                                "conditions": string
                            }},
                            "third_entry": {{
                                "percentage": float,
                                "conditions": string
                            }}
                        }}
                    }},
                    "market_timing": {{
                        "current_conditions": string,
                        "optimal_conditions": [string],
                        "additional_strategies": [string]
                    }},
                    "risk_management": {{
                        "beta": float,
                        "hedging_strategies": [string],
                        "monitoring_requirements": [string]
                    }}
                }}
            }}

            Previous Analysis: {analysis}
            """
            
            messages.append(HumanMessage(content=strategy_prompt))
            response = trading_strategist.invoke({"messages": messages})
            
            return {
                "messages": messages + [HumanMessage(content=str(response))],
                "analysis_results": {**state["analysis_results"], "trading_strategy": response},
                "current_agent": "execution_agent"
            }

        def execution_planning(state: AgentState):
            messages = state["messages"]
            strategy = state["analysis_results"]["trading_strategy"]
            
            # Retrieve relevant context for execution planning
            context_query = f"Create execution plans for {stock_selection} considering market conditions and liquidity"
            relevant_docs = rag_manager.retrieve_relevant_context(context_query, "execution_planning")
            context = rag_manager.format_context_for_prompt(relevant_docs)
            
            execution_prompt = f"""
            {context}
            
            Create execution plans for {stock_selection} and provide ONLY the JSON response in the following format:
            {{
                "execution_plan": {{
                    "entry_execution": {{
                        "tranche_1": {{
                            "price_target": float,
                            "order_type": string,
                            "size": string,
                            "timing": string,
                            "validity": string
                        }},
                        "tranche_2": {{
                            "price_target": float,
                            "order_type": string,
                            "size": string,
                            "timing": string,
                            "validity": string
                        }},
                        "tranche_3": {{
                            "price_target": float,
                            "order_type": string,
                            "size": string,
                            "timing": string,
                            "validity": string
                        }}
                    }},
                    "exit_parameters": {{
                        "profit_taking": {{
                            "level_1": {{
                                "price": float,
                                "size": string,
                                "order_type": string
                            }},
                            "level_2": {{
                                "price": float,
                                "size": string,
                                "order_type": string
                            }}
                        }},
                        "stop_loss": {{
                            "initial": {{
                                "price": float,
                                "order_type": string,
                                "limit_offset": float
                            }}
                        }}
                    }},
                    "execution_considerations": {{
                        "liquidity_analysis": {{
                            "avg_daily_volume": string,
                            "recommended_max_order_size": string,
                            "expected_slippage": string
                        }},
                        "timing_optimization": {{
                            "preferred_trading_hours": string,
                            "avoid_periods": [string],
                            "special_considerations": string
                        }},
                        "cost_analysis": {{
                            "estimated_commission": string,
                            "expected_slippage_cost": string,
                            "total_cost_estimate": string
                        }}
                    }},
                    "contingency_plans": {{
                        "gap_down": string,
                        "high_volatility": string,
                        "low_liquidity": string,
                        "technical_issues": string
                    }}
                }}
            }}

            Trading Strategy: {strategy}
            """
            
            messages.append(HumanMessage(content=execution_prompt))
            response = execution_agent.invoke({"messages": messages})
            
            return {
                "messages": messages + [HumanMessage(content=str(response))],
                "analysis_results": {**state["analysis_results"], "execution_plan": response},
                "current_agent": "risk_manager"
            }

        def risk_assessment(state: AgentState):
            messages = state["messages"]
            execution_plan = state["analysis_results"]["execution_plan"]
            
            # Retrieve relevant context for risk assessment
            context_query = f"Evaluate risks for {stock_selection} considering market conditions and regulatory environment"
            relevant_docs = rag_manager.retrieve_relevant_context(context_query, "risk_assessment")
            context = rag_manager.format_context_for_prompt(relevant_docs)
            
            risk_prompt = f"""
            {context}
            
            Evaluate risks for {stock_selection} and provide your response in the following JSON format:
            {{
                "risk_assessment": {{
                    "market_risk_factors": {{
                        "beta": float,
                        "sector_exposure": {{
                            "sector": string,
                            "correlation_to_sector": float,
                            "sector_cyclicality": string
                        }},
                        "volatility_metrics": {{
                            "historical_volatility": float,
                            "risk_level": string,
                            "volatility_trend": string
                        }}
                    }},
                    "portfolio_impact": {{
                        "position_size_recommendation": string,
                        "diversification_impact": string,
                        "risk_contribution": float
                    }},
                    "risk_mitigation_strategies": [
                        {{
                            "strategy": string,
                            "description": string,
                            "implementation": string
                        }}
                    ]
                }}
            }}
            
            Use the provided execution plan to inform your risk assessment.
            Execution Plan: {execution_plan}
            """
            
            messages.append(HumanMessage(content=risk_prompt))
            response = risk_manager.invoke({"messages": messages})
            
            return {
                "messages": messages + [HumanMessage(content=str(response))],
                "analysis_results": {**state["analysis_results"], "risk_assessment": response},
                "current_agent": "end"
            }

        # Add nodes to the graph
        workflow.add_node("data_analyst", data_analysis)
        workflow.add_node("trading_strategist", trading_strategy)
        workflow.add_node("execution_agent", execution_planning)
        workflow.add_node("risk_manager", risk_assessment)

        # Define edges
        workflow.add_edge(START, "data_analyst")
        workflow.add_edge("data_analyst", "trading_strategist")
        workflow.add_edge("trading_strategist", "execution_agent")
        workflow.add_edge("execution_agent", "risk_manager")
        workflow.add_edge("risk_manager", END)

        # Compile the graph
        app = workflow.compile()

        # Initialize state
        initial_state = {
            "messages": [],
            "stock_data": stock_data,
            "analysis_results": {},
            "current_agent": "data_analyst"
        }

        # Run the analysis
        final_state = app.invoke(initial_state)

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
            },
            'analysis': final_state["analysis_results"]
        }

        return final_result

    except Exception as e:
        logger.error(f"Error in analyze_stock for {stock_selection}: {str(e)}")
        raise Exception(f"Analysis failed: {str(e)}") 