import unittest
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategy import get_iv_and_greeks

class TestGetIVAndGreeks(unittest.TestCase):
    def test_get_iv_and_greeks(self):
        # Test with no specific expiry (should get all expiries)
        result = get_iv_and_greeks()
        # print(result)
        # Verify the result is a dictionary
        self.assertIsInstance(result, dict)
        
        # If we got any data, verify the structure
        if result:
            # Get first option's data
            first_option = next(iter(result.values()))
            
            # Verify all required fields are present and have correct types
            self.assertIn('iv', first_option)
            self.assertIn('delta', first_option)
            self.assertIn('underlying', first_option)
            self.assertIn('bid', first_option)
            self.assertIn('ask', first_option)
            
            # Verify numeric fields are floats
            self.assertIsInstance(first_option['iv'], float)
            self.assertIsInstance(first_option['delta'], float)
            self.assertIsInstance(first_option['underlying'], float)
            self.assertIsInstance(first_option['bid'], float)
            self.assertIsInstance(first_option['ask'], float)
            
            # Verify IV is between 0 and 1 (as it's a decimal)
            self.assertGreaterEqual(first_option['iv'], 0)
            self.assertLessEqual(first_option['iv'], 1)
            
            # Verify delta is between -1 and 1
            self.assertGreaterEqual(first_option['delta'], -1)
            self.assertLessEqual(first_option['delta'], 1)
            
            # Verify underlying price is positive
            self.assertGreater(first_option['underlying'], 0)

    def test_get_iv_and_greeks_with_expiry(self):
        # Get the next Friday's date
        today = datetime.now()
        days_until_friday = (4 - today.weekday()) % 7
        next_friday = today + timedelta(days=days_until_friday)
        
        # Format the date in Bybit's format (e.g., 25DEC22)
        expiry_date = next_friday.strftime("%d%b%y").upper()
        print(f"Testing with expiry date: {expiry_date}")
        
        # Test with specific expiry date
        result = get_iv_and_greeks(expiry=expiry_date)
        print(f"Result: {result}")
        
        # Verify the result is a dictionary
        self.assertIsInstance(result, dict)
        
        # If we got any data, verify the structure
        if result:
            # Get first option's data
            first_option = next(iter(result.values()))
            
            # Verify all required fields are present and have correct types
            self.assertIn('iv', first_option)
            self.assertIn('delta', first_option)
            self.assertIn('underlying', first_option)
            self.assertIn('bid', first_option)
            self.assertIn('ask', first_option)
            
            # Verify numeric fields are floats
            self.assertIsInstance(first_option['iv'], float)
            self.assertIsInstance(first_option['delta'], float)
            self.assertIsInstance(first_option['underlying'], float)
            self.assertIsInstance(first_option['bid'], float)
            self.assertIsInstance(first_option['ask'], float)
            
            # Verify IV is between 0 and 1 (as it's a decimal)
            self.assertGreaterEqual(first_option['iv'], 0)
            self.assertLessEqual(first_option['iv'], 1)
            
            # Verify delta is between -1 and 1
            self.assertGreaterEqual(first_option['delta'], -1)
            self.assertLessEqual(first_option['delta'], 1)
            
            # Verify underlying price is positive
            self.assertGreater(first_option['underlying'], 0)
            
            # Verify that all options in the result have the correct expiry date
            for symbol in result.keys():
                # Extract expiry from symbol (format: BTC-25DEC22-XXXXX-C/P)
                symbol_expiry = symbol.split('-')[1]
                self.assertEqual(symbol_expiry, expiry_date)

if __name__ == '__main__':
    unittest.main() 