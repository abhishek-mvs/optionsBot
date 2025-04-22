from bybit_apis import DMABybit
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
bybit = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")

def get_pnl_of_sqaured_position(order_link_id_sell, order_link_id_buy):
    
    sell_order_response = bybit.get_order_details(order_link_id_sell)
    buy_order_response = bybit.get_order_details(order_link_id_buy)
    
    # Extract order details from the response
    sell_order = sell_order_response.get('result', {}).get('list', [{}])[0]
    buy_order = buy_order_response.get('result', {}).get('list', [{}])[0]
    
    # Calculate PnL based on execution values and fees
    sell_value = float(sell_order.get('cumExecValue', 0))
    sell_fee = float(sell_order.get('cumExecFee', 0))
    buy_value = float(buy_order.get('cumExecValue', 0))
    buy_fee = float(buy_order.get('cumExecFee', 0))
    
    pnl = sell_value - buy_value - sell_fee - buy_fee
    return pnl

def get_pnl_of_open_position(symbol):
    open_positions = bybit.get_open_positions(symbol=symbol)
    # Check if the API response is valid
    if open_positions.get('retCode') != 0 or 'result' not in open_positions:
        return 0  # Return 0 if there's an error or no result
    
    position_list = open_positions.get('result', {}).get('list', [])
    
    # If no positions found
    if not position_list:
        return 0
    
    # Get the position for the specified symbol
    position = position_list[0]
    
    # Extract unrealized PnL (current PnL)
    unrealised_pnl = float(position.get('unrealisedPnl', 0))
    
    # Extract realized PnL
    realised_pnl = float(position.get('curRealisedPnl', 0))
    
    # Calculate total PnL
    total_pnl = unrealised_pnl + realised_pnl
    
    return total_pnl

def get_initial_margin(symbol):
   position_response = bybit.get_open_positions(symbol=symbol)
   position = position_response.get('result', {}).get('list', [{}])[0]
   return float(position.get('positionIM', 0))

def get_initial_margin_of_position_state(position_state):
    total_initial_margin = 0
    for position_type, position_info in position_state.items():
        if position_info.get("symbol"):
            symbol = position_info["symbol"]
            initial_margin = get_initial_margin(symbol)
            total_initial_margin += initial_margin
    return total_initial_margin
def get_pnl_of_position_state(position_state):
    total_pnl = 0
    
    # Iterate through all positions in the position state
    for position_type, position_info in position_state.items():
        if position_info.get("symbol"):
            symbol = position_info["symbol"]
            position_pnl = get_pnl_of_open_position(symbol)
            total_pnl += position_pnl
    
    return total_pnl