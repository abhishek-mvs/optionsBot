import time
import requests
import csv
import argparse
# from datetime import datetime, UTC
from datetime import datetime, timezone
from bybit_apis import DMABybit
import os
from dotenv import load_dotenv
import logging

# Initialize global variables
total_realized_pnl = 0.0
intital_margin_prices = 0.0

# Create logs directory if it doesn't exist
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Create data directory if it doesn't exist
data_dir = 'trades_data'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Configure logging with timestamped filename in logs directory
log_filename = os.path.join(logs_dir, f'strategy_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # This will also print to console
    ]
)

# Initialize Bybit API client
load_dotenv()
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
bybit_client = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT", category="option")

# Logging: Initialize CSV file with headers if not exists
LOG_FILE = os.path.join(data_dir, f'trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
with open(LOG_FILE, mode='w', newline='') as f:
   writer = csv.writer(f)
   writer.writerow(["Timestamp", "Symbol", "Side", "Quantity", "Price", "Realized_PnL"])
 
def log_trade(symbol, side, qty, price, realized_pnl):
   """Log the trade details and P&L to the CSV file."""
   timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
   with open(LOG_FILE, mode='a', newline='') as f:
       writer = csv.writer(f)
       writer.writerow([timestamp, symbol, side, qty, price, f"{realized_pnl:.4f}"])
   logging.info(f"Trade logged: {symbol} {side} {qty} @ {price} (PnL: {realized_pnl:.4f})")
 
# Helper: Fetch current option market data (tickers) for BTC
def get_iv_and_greeks(expiry=None):
   """Fetch all BTC option tickers and return parsed data (IV, delta, etc.)"""
   data = bybit_client.get_tickers(category="option", base_coin="BTC", exp_date=expiry)
   if data.get("retCode") != 0:
       raise Exception(f"Failed to get tickers: {data.get('retMsg')}")
   # Parse the returned list of option tickers
   option_list = data["result"]["list"]
   # Convert list of tickers to a dict for easier search: key by symbol
   options_data = {}
   for opt in option_list:
       symbol = opt["symbol"]
       # Extract needed fields
       iv = float(opt.get("markIv", 0))         # implied volatility (as a decimal, e.g. 0.75 for 75%)
       delta = float(opt.get("delta", 0))
       underlying = float(opt.get("underlyingPrice", 0))
       options_data[symbol] = {
           "iv": iv,
           "delta": delta,
           "underlying": underlying,
           "bid": float(opt.get("bid1Price", 0)),
           "ask": float(opt.get("ask1Price", 0))
       }
   return options_data
 
# Helper: Identify a call and put with delta ~ +0.1 and -0.1 respectively
def find_delta_neutral_legs(options_data):
   """Find one call and one put whose deltas are approximately +0.1 and -0.1."""
   target_delta = 0.1
   best_call = None
   best_put = None
   delta_diff_call = float("inf")
   delta_diff_put = float("inf")
   for symbol, info in options_data.items():
       d = info["delta"]
       # Ensure we pick only BTCUSDT options (Bybit might list BTCUSD etc; focusing on USDT-settled if needed)
       # For simplicity, assume all here are BTC options for the chosen expiry.
       # Identify calls vs puts by symbol structure (e.g., "-C" or "-P")
       if symbol.endswith("-C-USDT"):  # call option
           # We want a call with delta ~ +0.1 (d should be positive)
           if d > 0:
               diff = abs(d - target_delta)
               if diff < delta_diff_call:
                   delta_diff_call = diff
                   best_call = (symbol, info)
       elif symbol.endswith("-P-USDT"):  # put option
           # We want a put with delta ~ -0.1 (d should be negative)
           if d < 0:
               diff = abs(d + target_delta)  # use + because d is negative, want d ≈ -0.1
               if diff < delta_diff_put:
                   delta_diff_put = diff
                   best_put = (symbol, info)
   return best_call, best_put
 
# Helper: Place an order (using requests for illustration; normally use authenticated request)
def place_order(side, symbol, qty, order_type="Market", price=None):
   logging.info(f"Placing order: {symbol} {side} {qty} {order_type} {price}")
   return 1
   """Place an order on Bybit for the given option. side: 'Buy' or 'Sell'. Returns order ID or raises on error."""
   body = {
       "symbol": symbol,
       "side": side,
       "orderType": order_type,
       "qty": str(qty),  # Convert quantity to string as required by Bybit
       "category": "option",  # Required for options trading
       "timeInForce": "IOC" if order_type == "Market" else "GTC"  # IOC for market orders, GTC for limit orders
   }
   if price is not None:
       body["price"] = str(price)  # Convert price to string as required by Bybit
   
   result = bybit_client.place_order(body)
   if result.get("retCode") != 0:
       raise Exception(f"Order placement failed: {result.get('retMsg')}")
   order_id = result["result"]["orderId"]
   return order_id
 
# Strategy functions
def enter_delta_neutral_position(expiry=None):
   """Monitor IV and enter delta-neutral short position on IV spike."""
   # Monitor until IV spike condition met
   baseline_iv = None
   spike_triggered = False
   selected_call = selected_put = None
   selected_call_info = selected_put_info = None
 
   logging.info("Monitoring IV for a spike...")
   while not spike_triggered:
       data = get_iv_and_greeks(expiry)
       logging.info("get_iv_and_greeks data:")
       # Compute an aggregate IV measure (e.g., ATM IV or average of near-the-money options)
       # For simplicity, take IV of ATM call as baseline indicator:
       # Find option with delta closest to 0.5 (ATM) to represent ATM IV
       delta = None
       atm_diff = float("inf")
       atm_iv = None
       atm_sym = None
       for sym, info in data.items():
           if sym.endswith("-C-USDT"):  # check call (could also consider put)
               diff = abs(info["delta"] - 0.5)
               if diff < atm_diff:
                   atm_diff = diff
                   atm_iv = info["iv"]
                   delta = info["delta"]
                   atm_sym = sym
       if atm_iv is None:
           logging.warning("No ATM IV found, trying again...")
           time.sleep(5)
           continue  # no data, try again
       logging.info(f"atm_sym: {atm_sym}")
       logging.info(f"atm_iv: {atm_iv}")
       logging.info(f"delta: {delta}")
       
       if baseline_iv is None:
           # initialize baseline (could use a moving average; here just first sample)
           baseline_iv = atm_iv
       # Check for +30% spike
       if atm_iv >= 1.3 * baseline_iv or True:
           spike_triggered = True
           # Identify the 0.1 delta call and -0.1 delta put for entry
           (call_sym, call_info), (put_sym, put_info) = find_delta_neutral_legs(data)
           selected_call, selected_call_info = call_sym, call_info
           selected_put, selected_put_info = put_sym, put_info
           logging.info(f"IV spike detected! ATM IV {atm_iv:.2f} vs baseline {baseline_iv:.2f}.")
           logging.info(f"Selected call: {selected_call} (delta {selected_call_info['delta']:.2f})")
           logging.info(f"Selected put:  {selected_put} (delta {selected_put_info['delta']:.2f})")
       else:
           # Update baseline gradually (to adapt to slowly rising volatility, avoiding one-off spikes)
           baseline_iv = 0.9 * baseline_iv + 0.1 * atm_iv
           logging.info(f"No spike yet. Current ATM IV={atm_iv:.2f}, baseline={baseline_iv:.2f}.")
           time.sleep(1)  # wait 1 minute before next check
   
   # Place orders for the selected legs (short call and short put)
   call_symbol = selected_call
   put_symbol = selected_put
   # We'll sell 1 contract each for now
   order_id_call = place_order(side="Sell", symbol=call_symbol, qty=0.01)
   order_id_put  = place_order(side="Sell", symbol=put_symbol, qty=0.01)
   logging.info(f"Entered short position: Sold 1x {call_symbol} and 1x {put_symbol}.")
   # Log the entry trades (realized PnL = 0 for entry since just opening positions)
   # Assuming we have price info from selected_call_info (bid/ask). Use bid for sell price as conservative.
   entry_call_price = selected_call_info["bid"] or selected_call_info["ask"]  # if bid is 0 (no bid), use ask as proxy
   entry_put_price  = selected_put_info["bid"] or selected_put_info["ask"]
   log_trade(call_symbol, "Sell", 0.01, entry_call_price, realized_pnl=0.0)
   log_trade(put_symbol,  "Sell", 0.01, entry_put_price,  realized_pnl=0.0)
   global intital_margin_prices
   intital_margin_prices = entry_call_price + entry_put_price
   # Return a structure representing current position state
   position_state = {
       "call": {"symbol": call_symbol, "delta": selected_call_info["delta"], "entry_price": entry_call_price, "contracts": 1, "qty": 0.01},
       "put":  {"symbol": put_symbol,  "delta": selected_put_info["delta"],  "entry_price": entry_put_price,  "contracts": 1, "qty": 0.01}
   }
   return position_state

def calculate_current_pnl(position_state, get_iv_and_greeks_data, expiry=None):
    """Calculate current PnL for the position including both realized and unrealized components."""
    unrealized_pnl = 0.0
    for leg, info in position_state.items():
        symbol = info["symbol"]
        entry_price = info["entry_price"]
        contracts = info["contracts"]
        current_price = get_iv_and_greeks_data.get(symbol, {}).get("bid") or get_iv_and_greeks_data.get(symbol, {}).get("ask") or 0.0
        # For short positions, PnL = entry_price - current_price
        unrealized_pnl += (entry_price - current_price) * contracts
    
    # Total PnL = realized PnL + unrealized PnL
    total_pnl = total_realized_pnl + unrealized_pnl
    logging.info(f"Total PnL: {total_pnl:.4f} (Realized: {total_realized_pnl:.4f}, Unrealized: {unrealized_pnl:.4f})")
    return total_pnl

def check_pnl_and_exit(position_state, get_iv_and_greeks_data, expiry=None):
    """Check PnL and exit if it's too low."""
    current_pnl = calculate_current_pnl(position_state, get_iv_and_greeks_data, expiry)
    logging.info(f"Current PnL: {current_pnl} and intital_margin_prices: {intital_margin_prices}")
    # Get current market data
    # Check if PnL is above initial margin prices plus 10% (profit target)
    global total_realized_pnl
    if current_pnl >= intital_margin_prices * 0.1:
        logging.info(f"Profit target reached! Current PnL: {current_pnl:.4f}, which is above initial margin plus 10%: {(intital_margin_prices * 0.1):.4f}")
        # Close positions (buy back what we sold)
        for leg, info in position_state.items():
            symbol = info["symbol"]
            qty = info["qty"]
            contracts = info["contracts"]
            current_price = get_iv_and_greeks_data.get(symbol, {}).get("ask") or get_iv_and_greeks_data.get(symbol, {}).get("bid") or 0.0
            entry_price = info["entry_price"]
            realized_pnl = (entry_price - current_price) * contracts
           
            total_realized_pnl += realized_pnl
            order_id = place_order(side="Buy", symbol=symbol, qty=qty)
            log_trade(symbol, "Buy", qty, current_price, realized_pnl=realized_pnl)
            logging.info(f"Closed {leg} position with realized PnL: {realized_pnl:.4f}")
        logging.info(f"Exited position with total realized PnL: {total_realized_pnl:.4f}")
        return True  # Signal that we've exited the position
    
    # Check if PnL is below initial margin prices minus 10% (stop loss)
    if current_pnl <= intital_margin_prices * -0.1:
        logging.info(f"Stop loss triggered! Current PnL: {current_pnl:.4f}, which is below initial margin minus 10%: {intital_margin_prices * -0.1:.4f}")
        # Close positions (buy back what we sold)
        for leg, info in position_state.items():
            symbol = info["symbol"]
            qty = info["qty"]
            contracts = info["contracts"]
            current_price = get_iv_and_greeks_data.get(symbol, {}).get("ask") or get_iv_and_greeks_data.get(symbol, {}).get("bid") or 0.0
            entry_price = info["entry_price"]
            realized_pnl = (entry_price - current_price) * contracts
            
            total_realized_pnl += realized_pnl
            order_id = place_order(side="Buy", symbol=symbol, qty=qty)
            log_trade(symbol, "Buy", qty, current_price, realized_pnl=realized_pnl)
            logging.info(f"Closed {leg} position with realized PnL: {realized_pnl:.4f}")
        logging.info(f"Exited position with total realized PnL: {total_realized_pnl:.4f}")
        return True  # Signal that we've exited the position
    
    # If we're here, we're within our PnL thresholds
    logging.info(f"Current PnL: {current_pnl:.4f} is within acceptable range of initial margin ±10%: {intital_margin_prices:.4f} ±{intital_margin_prices * 0.1:.4f}")
    return False  # Signal that we're still in the position

def rebalance_delta(position_state, expiry=None):
   """Check portfolio delta and rebalance if outside ±0.1 by adjusting the appropriate leg."""
   logging.info(f"Rebalancing delta: {position_state}")
   data = get_iv_and_greeks(expiry)
   exit_signal = check_pnl_and_exit(position_state, data, expiry)
   if exit_signal:
       return {}
   # Calculate current net delta of the portfolio
   call_sym = position_state["call"]["symbol"]
   put_sym  = position_state["put"]["symbol"]
   call_delta = data.get(call_sym, {}).get("delta", 0) * position_state["call"]["contracts"]
   put_delta  = data.get(put_sym, {}).get("delta", 0) * position_state["put"]["contracts"]
   net_delta = call_delta + put_delta
   logging.info(f"Current net delta: {net_delta:.3f} (call leg {call_delta:.3f}, put leg {put_delta:.3f})")
   if abs(net_delta) <= 0.1:
       logging.info("Portfolio delta is within ±0.1, no rebalance needed at this interval.")
       return None  # no adjustment made
   
   # Determine which leg has smaller delta contribution in magnitude
   if abs(call_delta) < abs(put_delta):
       leg_to_adjust = "call"
   else:
       leg_to_adjust = "put"
   # Decide adjustment: we will add one more short contract on the weaker side
   adjust_symbol = position_state[leg_to_adjust]["symbol"]
   # Close the existing position, we have to buy since we are short
   price = data.get(adjust_symbol, {}).get("bid") or data.get(adjust_symbol, {}).get("ask") or 0.0
   entry_price = position_state[leg_to_adjust]["entry_price"]
   contracts = position_state[leg_to_adjust]["contracts"]
   realized_pnl = (entry_price - price) * contracts  # Since we're short, PnL = entry_price - current_price
   global total_realized_pnl
   total_realized_pnl += realized_pnl
   order_id = place_order(side="Buy", symbol=adjust_symbol, qty=0.01)
   log_trade(adjust_symbol, "Buy", 0.01, price, realized_pnl=realized_pnl)
   
   new_adjust_symbol = get_position_near_delta(data, leg_to_adjust, abs(put_delta) if leg_to_adjust == "call" else abs(call_delta))
   order_id_new_symbol = place_order(side="Sell", symbol=new_adjust_symbol, qty=0.01)
   new_adjust_price = data.get(new_adjust_symbol, {}).get("bid") or data.get(new_adjust_symbol, {}).get("ask") or 0.0
   position_state[leg_to_adjust] = {"symbol": new_adjust_symbol,  "delta": data.get(new_adjust_symbol, {}).get("delta", 0),  "entry_price": new_adjust_price,  "contracts": 1, "qty": 0.01}
   # Log the adjustment trade. Realized PnL = 0 (we are opening new position, not closing any).
   log_trade(new_adjust_symbol, "Sell", 0.01, new_adjust_price, realized_pnl=0.0)
   logging.info(f"New position state after rebalancing: {position_state}")
   return position_state  # adjustment made
 
def get_position_near_delta(get_iv_and_greeks_data, leg_to_adjust, target_delta):
   """Get the position near the delta"""
   symbol_ends_with = "-C-USDT" if leg_to_adjust == "call" else "-P-USDT"
   best_symbol = None
   delta_diff_call = float("inf")
   delta_diff_put = float("inf")
   
   for symbol, info in get_iv_and_greeks_data.items():
        d = info["delta"]
        if symbol.endswith(symbol_ends_with):
            if symbol_ends_with == "-C-USDT":  # call option
                # We want a call with delta ~ target_delta (d should be positive)
                if d > 0:
                    diff = abs(d - target_delta)
                    if diff < delta_diff_call:
                        delta_diff_call = diff
                        best_symbol = symbol
            else:  # put option
                # We want a put with delta ~ -target_delta (d should be negative)
                if d < 0:
                    diff = abs(d + target_delta)  # Note the + sign here for puts
                    if diff < delta_diff_put:
                        delta_diff_put = diff
                        best_symbol = symbol
   return best_symbol
   
def convert_to_iron_butterfly(position_state, expiry=None):
   """If the short positions form a straddle, buy wings to form an iron butterfly."""
   logging.info(f"Converting to iron butterfly: {position_state}")
   # Determine current short strikes for call and put
   call_strike = float(position_state["call"]["symbol"].split("-")[-3])  # e.g., symbol format "BTC-<expiry>-<strike>-C-USDT"
   put_strike  = float(position_state["put"]["symbol"].split("-")[-3])
   print(f"call_strike: {call_strike}, put_strike: {put_strike}")
   # Check if strikes are effectively equal (or very close) indicating a straddle
   if abs(call_strike - put_strike) > 1e-6:
       return False  # not a straddle yet
   center_strike = call_strike  # (which equals put_strike)
   
   # Initialize wing options
   chosen_call_wing = None
   chosen_put_wing = None
   
   # Get market data for available options
   data = get_iv_and_greeks(expiry)
   
   # Find the closest call option above center strike and put option below center strike
   min_diff_call = float("inf")
   min_diff_put = float("inf")
   
   for sym, info in data.items():
       if sym.endswith("-C-USDT"):
           strike = float(sym.split("-")[-3])
           if strike > center_strike and abs(strike - center_strike) < min_diff_call:
               min_diff_call = abs(strike - center_strike)
               chosen_call_wing = sym
       elif sym.endswith("-P-USDT"):
           strike = float(sym.split("-")[-3])
           if strike < center_strike and abs(strike - center_strike) < min_diff_put:
               min_diff_put = abs(strike - center_strike)
               chosen_put_wing = sym
   
   print(f"center_strike: {center_strike}")
   print(f"chosen_call_wing: {chosen_call_wing}, chosen_put_wing: {chosen_put_wing}")
   if not chosen_call_wing or not chosen_put_wing:
       logging.warning("Could not find suitable wing strikes for iron butterfly.")
       return False
 
   # Place buy orders for the wings
   order_id1 = place_order(side="Buy", symbol=chosen_call_wing, qty=0.01)
   order_id2 = place_order(side="Buy", symbol=chosen_put_wing, qty=0.01)
   # Calculate cost of wings and total credit from shorts
   wing_call_price = data.get(chosen_call_wing, {}).get("ask") or 0.0
   wing_put_price  = data.get(chosen_put_wing, {}).get("ask") or 0.0
   total_wing_cost = wing_call_price + wing_put_price
   # Calculate total premium received from shorts (approximate using entry prices * contracts)
   total_short_premium = (position_state["call"]["entry_price"] * position_state["call"]["contracts"] +
                          position_state["put"]["entry_price"] * position_state["put"]["contracts"])
   net_credit_after_wings = total_short_premium - total_wing_cost
   logging.info(f"Added wings: Bought 1x {chosen_call_wing} and 1x {chosen_put_wing}. Total wing cost ~{total_wing_cost:.2f}, net credit remaining ~{net_credit_after_wings:.2f}.")
   # Log the wing purchase trades (realized PnL negative here as cost, but we treat it as part of strategy P&L)
   log_trade(chosen_call_wing, "Buy", 1, wing_call_price, realized_pnl=0.0)
   log_trade(chosen_put_wing,  "Buy", 1, wing_put_price,  realized_pnl=0.0)
   # Once wings are added, the position is now an iron butterfly with defined risk.
   return True
 
def main():
    parser = argparse.ArgumentParser(description='Run options trading strategy')
    parser.add_argument('--expiry', type=str, help='Expiry date in format DDMMMYY (e.g., 21APR25)', default="21APR25")
    args = parser.parse_args()
    
    print("Starting strategy execution")
    
    # Use expiry from command line argument
    expiry = args.expiry
    logging.info("Starting strategy execution for expiry: %s", args.expiry)
    # Step 1: Enter position on IV spike
    position = enter_delta_neutral_position(expiry)
    # Step 2: Rebalance periodically until conversion condition met or until expiry
    adjustments_count = 0
    while True:
        time.sleep(15 * 60)  # wait 15 minutes

        adjusted = rebalance_delta(position, expiry)
        if adjusted is not None:
            if adjusted == {}:
                logging.info("All positions have been exited. Stopping strategy execution.")
                break
            else:
                position = adjusted
                adjustments_count += 1
        # Check if we should convert to iron butterfly
        if adjustments_count > 0:  # after at least one adjustment, consider conversion
            converted = convert_to_iron_butterfly(position, expiry)
            if converted:
                logging.info("Converted to Iron Butterfly structure. No further adjustments will be made.")
                break
        # Optionally, break out if near expiration or a certain time to avoid new adjustments
        # (not implemented for brevity)
 
# def find_delta_neutral_legs(options_data, S, r, T, price_threshold):
#    """Find delta-neutral legs and check against Black-Scholes price threshold."""
#    best_call, best_put = None, None
#    for symbol, info in options_data.items():
#        strike = float(symbol.split('-')[-2].replace('C', '').replace('P', '').replace('USDT', ''))
#        sigma = info['iv']
#        if symbol.endswith('-C'):
#            price = black_scholes_call(S, strike, T, r, sigma)
#            if price >= price_threshold and (best_call is None or abs(info['delta'] - 0.1) < abs(best_call[1]['delta'] - 0.1)):
#                best_call = (symbol, info)
#        elif symbol.endswith('-P'):
#            price = black_scholes_put(S, strike, T, r, sigma)
#            if price >= price_threshold and (best_put is None or abs(info['delta'] + 0.1) < abs(best_put[1]['delta'] + 0.1)):
#                best_put = (symbol, info)
#    return best_call, best_put
 
# def enter_delta_neutral_position(expiry, S, r, T, price_threshold):
#    """Monitor IV and enter delta-neutral short position if prices meet the threshold."""
#    # Get market data and filter options
#    options_data = get_iv_and_greeks(expiry)
#    # Find the appropriate call and put options
#    selected_call, selected_put = find_delta_neutral_legs(options_data, S, r, T, price_threshold)
   
#    if selected_call is None or selected_put is None:
#        print("No suitable options meeting the price threshold were found.")
#        return
   
   # Further code to place orders if both options are found and meet the criteria...
 
if __name__ == "__main__":
    main()
 
 
 