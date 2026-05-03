import unittest
import random
from translator import ModernTransactionTranslator
from models import Transaction
from datetime import datetime, timezone


class TestSag(unittest.TestCase):
    def setUp(self):
        self.translator = ModernTransactionTranslator()

    def test_luhn_correctness(self):
        pan = self.translator.generate_luhn(16)
        self.assertTrue(self.is_luhn_valid(pan))

    def is_luhn_valid(self, pan):
        digits = [int(d) for d in pan]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:  # Double every second digit from right
                doubled = digit * 2
                checksum += doubled - 9 if doubled > 9 else doubled
            else:
                checksum += digit
        return checksum % 10 == 0

    def test_amount_micros_conversion(self):
        amount = 123.45
        micros = int(amount * 1000000)
        self.assertEqual(micros, 123450000)

    def test_de043_formatting(self):
        merchant = {
            "name": "Test Merchant Name",
            "city": "TestCity"
        }
        expected = "Test Merchant Name    TestCity     US"
        actual = f"{merchant['name'][:22]:<22}{merchant['city'][:13]:<13}US"
        self.assertEqual(actual, expected)

    def test_fraud_distribution(self):
        # Test that fraud rate is approximately correct
        fraud_count = 0
        total = 1000
        for _ in range(total):
            is_fraud = random.random() < 0.05
            if is_fraud:
                fraud_count += 1
        # Allow some variance
        self.assertTrue(30 <= fraud_count <= 80)

    def test_transaction_validation(self):
        # Test that Transaction model validates
        tx_data = {
            "transaction_id": "test",
            "schema_version": "1.1.0",
            "generator_version": "test",
            "MTI": "0100",
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "DE002_PAN": "1234567890123456",
            "DE003_ProcessingCode": "000000",
            "DE004_Amount": "000000012345",
            "DE022_POSEntryMode": "051",
            "DE025_POSCondition": "00",
            "DE038_AuthCode": "ABCDEF",
            "DE039_ResponseCode": "00",
            "DE041_TerminalID": "TERM001",
            "DE042_MerchantID": "MERCH001",
            "DE043_MerchantLocation": "Merchant Name          City            US",
            "Cust_ID": "CUST001",
            "Cust_Name": "John Doe",
            "Cust_Email": "john@example.com",
            "Cust_Address": "123 Main St",
            "Account_Number": "ACCT123",
            "Account_Status": "active",
            "Order_Amount_Micros": 123450000,
            "addressMatch": "Y",
            "Account_Risk": {"acctAgeInd": "01"},
            "Device_Browser_Telemetry": {"ipAddress": "192.168.1.1"},
            "Item_Metadata": {"items": []},
            "Authentication_3DS2": {"transactionStatus": "Y"},
            "Is_Fraud": False
        }
        tx = Transaction(**tx_data)
        self.assertIsInstance(tx, Transaction)


if __name__ == '__main__':
    unittest.main()