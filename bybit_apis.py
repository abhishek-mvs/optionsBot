"""
Language: Python3

Step1: Install Requirements
pip3 install pynacl
pip3 install requests
pip3 install python-dotenv

Step2: Create .env file with contents
API_KEY=apikey
API_SECRET=secretkey

"""

import json
import os
import time
import urllib.parse
import uuid
from urllib.parse import urlparse, urlencode

import requests
from dotenv import load_dotenv

# Conditional import for pynacl (which provides ed25519 functionality)
try:
    from nacl.signing import SigningKey
except ImportError:
    print("pynacl library not found. Please install it with: pip install pynacl")
    SigningKey = None


class DMABybit:
    def __init__(self, api_key, api_secret, symbol, category="linear"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.coinswitch_url = "https://dma.coinswitch.co"
        self.category = category
        self.symbol = symbol

    def _generate_coinswitch_signature(self, method, endpoint, params=None):
        """Generate signature for Coinswitch API requests using pynacl"""
        if not SigningKey:
            raise ImportError("pynacl library is required for Coinswitch signature generation")

        params = params or {}
        epoch_time = str(int(time.time()))

        # Modify endpoint for GET requests with params
        unquote_endpoint = endpoint
        if method == "GET" and params:
            endpoint += ('&', '?')[urlparse(endpoint).query == ''] + urlencode(params)
            unquote_endpoint = urllib.parse.unquote_plus(endpoint)

        signature_msg = method + unquote_endpoint + epoch_time

        # Generate signature using pynacl
        secret_key_bytes = bytes.fromhex(self.api_secret)
        signing_key = SigningKey(secret_key_bytes)
        signed = signing_key.sign(signature_msg.encode('utf-8'))
        signature = signed.signature.hex()

        return {
            'X-AUTH-SIGNATURE': signature,
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-EPOCH': epoch_time
        }

    def _prepare_request(self, endpoint, method='GET', params=None, body=None):
        """Prepare and send Coinswitch API request"""
        # Prepare full URL
        full_url = f"{self.coinswitch_url}{endpoint}"

        # Get Coinswitch signature headers
        signature_headers = self._generate_coinswitch_signature(method, endpoint, params)

        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            **signature_headers
        }

        try:
            if method == 'GET':
                response = requests.get(full_url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(full_url, headers=headers, json=body)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check and return response
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            print(f"Request error: {e}")
            print(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response'}")
            return None

    def transfer_funds(self, direction, amount):
        """Funds Transfer"""
        endpoint = "/dma/api/v1/funds/transfer"
        body = {
            "client_txn_id": str(uuid.uuid4()),
            "direction": direction,
            "amount": amount
        }
        return self._prepare_request(endpoint, method='POST', body=body)

    def set_leverage(self, leverage):
        """Set leverage for the symbol"""
        endpoint = "/v5/position/set-leverage"
        body = {
            "symbol": self.symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage),
            "category": self.category
        }
        return self._prepare_request(endpoint, method='POST', body=body)

    def set_margin_mode(self, margin_mode):
        endpoint = "/v5/account/set-margin-mode"
        body = {
            "category": self.category,
            "setMarginMode": margin_mode
        }
        return self._prepare_request(endpoint, method='POST', body=body)

    def switch_isolated(self, trade_mode, leverage):
        """switch_isolated for the symbol"""
        endpoint = "/v5/position/switch-isolated"
        body = {
            "symbol": self.symbol,
            "tradeMode": trade_mode,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage),
            "category": self.category
        }
        return self._prepare_request(endpoint, method='POST', body=body)

    def switch_position_mode(self, mode, switch_all_symbols=True, coin="USDT"):
        """switch_position_mode for the symbol"""
        endpoint = "/v5/position/switch-mode"
        body = {
            "symbol": self.symbol,
            "mode": mode,
            "coin": coin,
            "category": self.category
        }

        if switch_all_symbols:
            body.pop('symbol')

        return self._prepare_request(endpoint, method='POST', body=body)

    def place_order(self, body):
        """Place a market order"""
        endpoint = "/v5/order/create"

        body['category'] = self.category
        if not body.get('symbol'):
            body['symbol'] = self.symbol
        if not body.get('orderLinkId'):
            body['orderLinkId'] = str(uuid.uuid4())

        print("place order body", body)
        return self._prepare_request(endpoint, method='POST', body=body)

    def get_order_details(self, order_link_id):
        """Retrieve specific order details"""
        endpoint = "/v5/order/realtime"
        params = {
            'symbol': self.symbol,
            'orderLinkId': order_link_id,
            'category': self.category
        }
        return self._prepare_request(endpoint, params=params)

    def get_open_positions(self, symbol=None):
        """Get open positions for the symbol"""
        endpoint = "/v5/position/list"
        params = {
            # 'baseCoin': self.symbol,
            # 'symbol': self.symbol,
            'category': self.category
        }
        if symbol:
            params['symbol'] = symbol
        return self._prepare_request(endpoint, params=params)

    def add_margin(self, margin_amount=1):
        """Add margin to the position"""
        endpoint = "/v5/position/add-margin"
        body = {
            "symbol": self.symbol,
            "margin": str(margin_amount),
            "category": self.category
        }
        return self._prepare_request(endpoint, method='POST', body=body)

    def remove_margin(self, margin_amount=1):
        """Remove margin from the position"""
        endpoint = "/v5/position/add-margin"
        body = {
            "symbol": self.symbol,
            "margin": str(-margin_amount),
            "category": self.category
        }
        return self._prepare_request(endpoint, method='POST', body=body)

    def get_trades(self, order_link_id):
        """Get trades for a specific order"""
        endpoint = "/v5/execution/list"
        params = {
            # 'symbol': self.symbol,
            # 'orderLinkId': order_link_id,
            'category': self.category
        }
        return self._prepare_request(endpoint, params=params)

    def get_position_closed_pnl(self, params):
        """Get position closed PNL"""
        endpoint = "/v5/position/closed-pnl"
        return self._prepare_request(endpoint, params=params)
    
    def post_move_position(self):
        """Get move position"""
        endpoint = "/v5/position/move-positions"
        body = {
            'category': self.category,
        }
        return self._prepare_request(endpoint, method='POST', body=body)
    
    def generate_socket_signature(self):
        """Funds Transfer"""
        endpoint = "/dma/api/v1/socket/signature"
        return self._prepare_request(endpoint, method='GET')


    def get_tickers(self, category=None, symbol=None, base_coin=None, exp_date=None):
        """
        Get tickers information
        
        Args:
            category (str, optional): Product type. spot, linear, inverse, option
            symbol (str, optional): Symbol name
            base_coin (str, optional): Base coin. For option only
            exp_date (str, optional): Expiry date. For option only. Format: 25DEC22
            
        Returns:
            dict: API response
        """
        endpoint = "/v5/market/tickers"
        params = {}
        
        if category:
            params['category'] = category
        if symbol:
            params['symbol'] = symbol
        if base_coin:
            params['baseCoin'] = base_coin
        if exp_date:
            params['expDate'] = exp_date
            
        return self._prepare_request(endpoint, params=params)
    
    def get_balance(self):
        endpoint = "/v5/account/wallet-balance"
        params = {
            "category": self.category,
            "accountType": "UNIFIED"
        }
        return self._prepare_request(endpoint, params=params)

def main():
    load_dotenv()
    # IMPORTANT: create a file named .env and store secrets in the format shown
    '''
    API_KEY=apikey
    API_SECRET=secretkey
    '''

    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('API_SECRET')
    trader = DMABybit(API_KEY, API_SECRET, symbol="BTCUSDT")

    # Generate Signature needed for socket connections
    socket_signature_result = trader.generate_socket_signature()
    print(json.dumps(socket_signature_result, indent=2))

    # # 0. Update switch_isolated
    # print("\n1. Switch Isolated")
    # leverage_result = trader.switch_isolated(trade_mode=1, leverage=5)  # 0: cross margin. 1: isolated margin
    # print(json.dumps(leverage_result, indent=2))
    #
    # # 0. Update switch_position_mode
    # print("\n1. Switch switch_position_mode")
    # leverage_result = trader.switch_position_mode(mode=3)  # Position mode. 0: Merged Single. 3: Both Sides
    # print(json.dumps(leverage_result, indent=2))

    # 1. Set leverage to 5x
    print("\n2. Setting Leverage:")
    leverage_result = trader.set_leverage(leverage=100)
    print(json.dumps(leverage_result, indent=2))

    # 2. Transfer funds
    print("\n2. Transfer Funds:")
    funds_transfer_result = trader.transfer_funds("IN", 1)
    print(json.dumps(funds_transfer_result, indent=2))

    # 3. Place order
    print("\n3. Placing Order:")
    body = {
        "side": "Buy",  # Sell/Buy
        "orderType": "Market",  # Market / Limit etc.,
        "qty": "0.001",  # Must be string
    }
    order_result = trader.place_order(body)
    print(json.dumps(order_result, indent=2))

    # Extract order link ID
    order_link_id = order_result['result']['orderLinkId']

    # 3.1 Get order details
    print("\n3.1 Getting Order Details:")
    order_details = trader.get_order_details(order_link_id)
    print(json.dumps(order_details, indent=2))

    # 4. Get Open Positions
    print("\n4. Getting Open Positions:")
    positions = trader.get_open_positions()
    print(json.dumps(positions, indent=2))

    # 5. Add $1 margin
    print("\n5. Adding $1 Margin:")
    add_margin_result = trader.add_margin(1)
    print(json.dumps(add_margin_result, indent=2))

    # 6. Get updated position info
    print("\n6. Getting Updated Position Info:")
    updated_positions = trader.get_open_positions()
    print(json.dumps(updated_positions, indent=2))

    # 7. Remove $1 margin
    print("\n7. Removing $1 Margin:")
    remove_margin_result = trader.remove_margin(1)
    print(json.dumps(remove_margin_result, indent=2))

    # 8. Get position info again
    print("\n8. Getting Final Position Info:")
    final_positions = trader.get_open_positions()
    print(json.dumps(final_positions, indent=2))

    # 9. Get trades for the order
    print("\n9. Getting Order Trades:")
    trades = trader.get_trades(order_link_id)
    print(json.dumps(trades, indent=2))


if __name__ == "__main__":
    main()
