import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategy import enter_delta_neutral_position

def test_enter_delta_neutral_position():
    # Get the next Friday's date
    today = datetime.now()
    days_until_friday = (4 - today.weekday()) % 7
    next_friday = today + timedelta(days=days_until_friday)
    expiry_date = next_friday.strftime("%d%b%y").upper()
    
    print(f"\nTesting enter_delta_neutral_position with expiry: {expiry_date}")
    print("Starting to monitor for IV spike...")
    
    # Call the function
    position_state = enter_delta_neutral_position(expiry="19APR25")
    
    print("\nFinal position state:")
    print(position_state)

if __name__ == '__main__':
    test_enter_delta_neutral_position() 