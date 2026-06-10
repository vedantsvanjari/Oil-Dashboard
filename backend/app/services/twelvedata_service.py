import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

if not TWELVE_DATA_API_KEY:
    logger.warning("TWELVE_DATA_API_KEY is missing from environment variables. Twelve Data integration may fail.")

def get_twelve_data_client():
    """
    Returns a configured client or session for Twelve Data API.
    Currently acts as a placeholder configuration to provide the API key.
    """
    if not TWELVE_DATA_API_KEY:
        logger.warning("Attempted to initialize Twelve Data client without an API key.")
        
    return {
        "api_key": TWELVE_DATA_API_KEY,
        "base_url": "https://api.twelvedata.com"
    }
