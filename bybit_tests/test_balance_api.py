import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from bybit_apis import DMABybit

def test_real_api():
    # Load environment variables
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('API_SECRET')
    
    if not API_KEY or not API_SECRET:
        print("Error: API_KEY and API_SECRET must be set in .env file")
        return
    
    # Initialize Bybit client for options
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTC", category="option")
    
    print("\n=== Testing Bybit Options API ===\n")
    
    # 1. Test get_open_positions for options
    print("1. Testing get_open_positions for options:")
    balance = bybit.get_balance()
    print(f"Response: {balance}\n")


if __name__ == "__main__":
    test_real_api() 