import json
import os
from datetime import datetime
from dotenv import load_dotenv
from bybit_apis import DMABybit

def test_option_apis():
    # Load environment variables
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('API_SECRET')
    
    if not API_KEY or not API_SECRET:
        print("Error: API_KEY and API_SECRET must be set in .env file")
        return
    
    # Initialize Bybit client for options
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    
    # Create output directory if it doesn't exist
    output_dir = "api_responses"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create timestamped output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"bybit_option_responses_{timestamp}.txt")
    
    print(f"\n=== Testing Bybit Option API Endpoints ===\n")
    print(f"Responses will be saved to: {output_file}\n")
    
    with open(output_file, 'w') as f:
        # 1. Test get_tickers for options
        f.write("1. Testing get_tickers for options:\n\n")
        
        f.write("   a. Testing all BTC options:\n")
        all_options = bybit.get_tickers(category="option", base_coin="BTC")
        f.write(f"   Response: {json.dumps(all_options, indent=2)}\n\n")
        
        f.write("   b. Testing BTC options for specific expiry (e.g., 25DEC25):\n")
        expiry_options = bybit.get_tickers(category="option", base_coin="BTC", exp_date="25DEC25")
        f.write(f"   Response: {json.dumps(expiry_options, indent=2)}\n\n")
        
        # 2. Test get_open_positions for options
        f.write("2. Testing get_open_positions for options:\n")
        positions = bybit.get_open_positions()
        f.write(f"   Response: {json.dumps(positions, indent=2)}\n\n")
        
        # 3. Test get_order_details for options
        f.write("3. Testing get_order_details for options:\n")
        f.write("   Note: This test requires a valid order_link_id\n\n")
        
        # 4. Test get_trades for options
        f.write("4. Testing get_trades for options:\n")
        f.write("   Note: This test requires a valid order_link_id\n\n")
    
    print(f"All responses have been saved to {output_file}")

if __name__ == "__main__":
    test_option_apis() 