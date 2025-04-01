# Add your utilities or helper functions to this file.

import os
from dotenv import load_dotenv, find_dotenv
from firebase_functions import params

# these expect to find a .env file at the directory above the lesson.
# the format for that file is (without the comment)
# API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService

def is_cloud_environment():
    """Check if we're running in a Firebase Cloud environment."""
    return os.getenv('FIREBASE_CONFIG') is not None

def get_secret(secret_name):
    """Get secret from Firebase Functions params."""
    if not is_cloud_environment():
        return None
    try:
        return params.SecretParam(secret_name).value
    except Exception:
        return None

def load_env():
    if not is_cloud_environment():
        _ = load_dotenv(find_dotenv())

def get_claude_api_key():
    # Try Firebase params first
    claude_api_key = get_secret("CLAUDE_API_KEY")
    if claude_api_key:
        return claude_api_key
        
    # Fall back to local environment
    load_env()
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    return claude_api_key

def get_openai_api_key():
    # Try Firebase params first
    openai_api_key = get_secret("OPENAI_API_KEY")
    if openai_api_key:
        return openai_api_key
        
    # Fall back to local environment
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in Firebase params or local environment")
    return openai_api_key

def get_serper_api_key():
    # Try Firebase params first
    serper_api_key = get_secret("SERPER_API_KEY")
    if serper_api_key:
        return serper_api_key
        
    # Fall back to local environment
    load_env()
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        raise ValueError("SERPER_API_KEY not found in Firebase params or local environment")
    return serper_api_key

def get_alpha_vantage_api_key():
    # Try Firebase params first
    alpha_vantage_api_key = get_secret("ALPHA_VANTAGE_API_KEY")
    if alpha_vantage_api_key:
        return alpha_vantage_api_key
        
    # Fall back to local environment
    load_env()
    alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not alpha_vantage_api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY not found in Firebase params or local environment")
    return alpha_vantage_api_key


# break line every 80 characters if line is longer than 80 characters
# don't break in the middle of a word
def pretty_print_result(result):
    parsed_result = []
    for line in result.split('\n'):
        if len(line) > 80:
            words = line.split(' ')
            new_line = ''
            for word in words:
                if len(new_line) + len(word) + 1 > 80:
                    parsed_result.append(new_line)
                    new_line = word
                else:
                    if new_line == '':
                        new_line = word
                    else:
                        new_line += ' ' + word
            parsed_result.append(new_line)
        else:
            parsed_result.append(line)
    return "\n".join(parsed_result)