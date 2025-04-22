from helpers import get_initial_margin, get_pnl_of_sqaured_position, get_pnl_of_open_position

def test_pnl_calculations():
    # Test squared position PnL
    print("\nTesting squared position PnL calculation:")
    order_link_id_sell = "your_sell_order_link_id"  # Replace with actual order link ID
    order_link_id_buy = "your_buy_order_link_id"    # Replace with actual order link ID
    # squared_pnl = get_pnl_of_sqaured_position(order_link_id_sell, order_link_id_buy)
    # print(f"Squared position PnL: {squared_pnl}")

    # Test open position PnL
    print("\nTesting open position PnL calculation:")
    symbol = "BTC-23APR25-92000-C-USDT"  # Replace with your symbol if different
    open_position_pnl = get_pnl_of_open_position(symbol)
    print(f"Open position PnL: {open_position_pnl}")

    initial_margin = get_initial_margin(symbol)
    print(f"Initial margin: {initial_margin}")

if __name__ == "__main__":
    test_pnl_calculations() 