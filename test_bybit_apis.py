import json
import os
from datetime import datetime
from dotenv import load_dotenv
from bybit_apis import DMABybit

# Global variables
API_KEY = None
API_SECRET = None

def test_transfer_funds():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    bybit.transfer_funds(amount=270, direction="IN")

def test_get_balance():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    balance = bybit.get_balance()
    print(balance)

def test_set_margin_mode():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    print(bybit.set_margin_mode("PORTFOLIO_MARGIN"))

def test_place_order():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    body = {
        "symbol": "BTC-23APR25-93000-C-USDT",
        # "symbol": "BTC-23APR25-89500-P-USDT",
        "side": "BUY",
        "qty": str(0.01),
        "orderType": "Market",
        "timeInForce": "IOC"
    }
    print(bybit.place_order(body))

def test_get_trade_history():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    print(bybit.get_trades(order_link_id="f1b91155-64ff-4f3d-8a21-7c118a003791"))

def test_move_position():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    print("post_move_position", bybit.post_move_position())

def test_get_position_closed_pnl():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    params = {
        "symbol": "BTC-23APR25-92000-C-USDT",
        "category": "option",
        "limit": 50
    }
    print("Closed PnL History:", bybit.get_position_closed_pnl(params))

def test_get_open_positions(symbol=None):
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    print("get_open_positions", bybit.get_open_positions(symbol=symbol))
    
def test_get_order_details():
    bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")
    print("get_order_details", bybit.get_order_details(order_link_id="68d246ae-d09c-4bd6-9642-e3b6e4d25016"))

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('API_SECRET')
    
    if not API_KEY or not API_SECRET:
        print("Error: API_KEY and API_SECRET must be set in .env file")
        exit(1)
        
    # test_transfer_funds()
    # test_option_apis() 
    # test_transfer_funds()
    # test_get_balance()
    # test_set_margin_mode()
    # test_place_order()
    # test_get_trade_history()
    # test_get_position_closed_pnl()
    # test_move_position()
    # test_get_open_positions()
    # test_get_order_details()
    # test_get_position_closed_pnl()