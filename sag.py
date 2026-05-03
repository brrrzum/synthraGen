import argparse
import json
import csv
import random
import string
import uuid
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker for dynamic, randomized geographic and PII data
fake = Faker()

# ==========================================
# 6. Industry Standards Generator
# ==========================================
class IndustryStandardGenerator:
    """Dynamic generator for all possible industry values to avoid hardcoded samples."""
    
    @staticmethod
    def generate_mcc():
        """Generates MCCs across all valid industry ranges."""
        industry_ranges = [
            (3000, 3350, "Airlines"),
            (3351, 3500, "Car Rental"),
            (3501, 3999, "Lodging/Hotels"),
            (4000, 4799, "Transportation Services"),
            (4800, 4999, "Utility/Telecomm Services"),
            (5000, 5599, "Retail & Grocery"),
            (5600, 5699, "Clothing Stores"),
            (5700, 5999, "Miscellaneous Retail"),
            (7000, 7299, "Personal Services"),
            (7300, 7999, "Business/Amusement Services"),
            (8000, 8999, "Professional/Medical Services")
        ]
        selected_range = random.choice(industry_ranges)
        mcc_code = str(random.randint(selected_range[0], selected_range[1])).zfill(4)
        return mcc_code, selected_range[2]

    @staticmethod
    def generate_processing_code():
        """DE 3: Generates 6-digit processing codes (Txn Type + From Acct + To Acct)[cite: 1]."""
        txn_types = ["00", "01", "09", "20", "31"] # Goods, Cash, Purchase with Cash, Refund, Inquiry
        acct_types = ["00", "10", "20", "30"] # Default, Savings, Checking, Credit
        return f"{random.choice(txn_types)}{random.choice(acct_types)}{random.choice(acct_types)}"

    @staticmethod
    def generate_pos_entry_mode():
        """DE 22: Generates valid 3-digit POS Entry Modes (PAN Entry + PIN Capability)[cite: 1]."""
        pan_entry = ["00", "01", "02", "05", "07", "10", "81", "90"] # Unknown, Manual, Magstripe, Chip, Contactless, COF, E-comm, Magstripe/Track2
        pin_capability = ["0", "1", "2", "8"] # Unknown, Terminal has PIN, Terminal does not have PIN, Down
        return f"{random.choice(pan_entry)}{random.choice(pin_capability)}"

    @staticmethod
    def generate_pos_condition_code():
        """DE 25: Generates valid 2-digit POS Condition Codes[cite: 1]."""
        return random.choice(["00", "01", "02", "03", "08", "59", "71"]) # Normal, Customer not present, Unattended, Merchant suspicious, Mail/Phone, E-commerce, Decline response

    @staticmethod
    def generate_response_code(is_fraud):
        """DE 39: Generates valid 2-digit Response Codes based on transaction state."""
        approved_codes = ["00", "08", "10", "11", "85"] # Approved, Honor with ID, Partial Approval, VIP, No reason to decline
        declined_codes = ["01", "04", "05", "14", "41", "43", "51", "54", "59", "91"] # Refer to issuer, Capture card, Do not honor, Invalid card, Lost, Stolen, Insufficient funds, Expired, Suspected fraud, Issuer inoperative
        return random.choice(declined_codes) if is_fraud else random.choice(approved_codes)

# ==========================================
# 4. ISO 8583 Translation Layer
# ==========================================
class ISO8583Translator:
    """Formats logical events into specific MTIs and data elements (DE)[cite: 1]."""
    
    @staticmethod
    def generate_luhn(length=16):
        """Generates a valid Primary Account Number (DE 2) using the Luhn algorithm[cite: 1]."""
        pan = [random.randint(1, 9) if i == 0 else random.randint(0, 9) for i in range(length - 1)]
        checksum = 0
        for i, digit in enumerate(reversed(pan)):
            if i % 2 == 0:
                doubled = digit * 2
                checksum += doubled - 9 if doubled > 9 else doubled
            else:
                checksum += digit
        pan.append((10 - (checksum % 10)) % 10)
        return "".join(map(str, pan))

    def format_transaction(self, cardholder, merchant, terminal, amount, is_fraud, timestamp):
        mti = "0100" # Authorization Request[cite: 1]
        de4_amount = f"{int(amount * 100):012d}" 
        
        # Dynamic ISO Elements generated from Industry Standards
        de3_processing_code = IndustryStandardGenerator.generate_processing_code()
        de22_pos_entry_mode = IndustryStandardGenerator.generate_pos_entry_mode()
        de25_pos_condition_code = IndustryStandardGenerator.generate_pos_condition_code()
        de39_response_code = IndustryStandardGenerator.generate_response_code(is_fraud)
        
        # 40-character Merchant Location Block (DE 43)[cite: 1]
        de43_location = f"{merchant['name'][:22]:<22}{merchant['city'][:13]:<13}{merchant['country'][:2]:<2}"
        
        # Authorization & Tokenization Data[cite: 1]
        de38_auth_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) if de39_response_code in ["00", "08", "10", "11", "85"] else ""
        de48_token = f"PAR-{uuid.uuid4().hex[:12].upper()}"
        
        return {
            "MTI": mti,
            "Timestamp": timestamp.isoformat(),
            "DE002_PAN": cardholder["pan"],
            "DE004_Amount": de4_amount,
            
            # Rich Customer Details via Faker
            "Cust_Name": cardholder["name"],
            "Cust_Email": cardholder["email"],
            "Cust_Phone": cardholder["phone"],
            "Cust_Address": cardholder["address"],
            "Cust_City": cardholder["city"],
            "Cust_State": cardholder["state"],
            "Cust_ZipCode": cardholder["zip_code"],
            
            # Digital Footprint & Demographics[cite: 1]
            "Device_ID": cardholder["device_id"],
            "IP_Address": cardholder["ip_address"],
            "CH_Age": cardholder["age"],
            "CH_Income": cardholder["income"],
            "CH_CreditScore": cardholder["credit_score"],
            
            # Base ISO details
            "DE003_ProcessingCode": de3_processing_code,
            "DE022_POSEntryMode": de22_pos_entry_mode,
            "DE025_POSCondition": de25_pos_condition_code,
            "DE038_AuthCode": de38_auth_code,
            "DE039_ResponseCode": de39_response_code,
            "DE041_TerminalID": terminal['id'],
            "DE042_MerchantID": merchant['id'],
            "DE043_MerchantLocation": de43_location,
            "DE048_TokenData": de48_token,
            "DE049_CurrencyCode": merchant['currency'],
            
            # Ground Truth for modeling[cite: 1]
            "Is_Fraud": is_fraud 
        }

# ==========================================
# 2. Population & Merchant Engine
# ==========================================
class PopulationEngine:
    def __init__(self, translator):
        self.translator = translator

    def generate_cardholders(self, count):
        cardholders = []
        for _ in range(count):
            cardholders.append({
                "id": f"CH-{uuid.uuid4().hex[:8].upper()}",
                "pan": self.translator.generate_luhn(),
                
                # Dynamic Faker PII
                "name": fake.name(),
                "email": fake.free_email(),
                "phone": fake.phone_number(),
                "address": fake.street_address(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "zip_code": fake.zipcode(),
                "device_id": str(uuid.uuid4()),
                "ip_address": fake.ipv4(),
                
                # Statistical Demographics[cite: 1]
                "age": int(random.gauss(40, 15)), 
                "income": round(random.lognormvariate(10.5, 0.5), 2),
                "credit_score": random.randint(300, 850) # Full FICO range
            })
        return cardholders

class MerchantEngine:
    def generate_merchants(self, count):
        merchants = []
        for _ in range(count):
            mcc_code, mcc_desc = IndustryStandardGenerator.generate_mcc()
            merchants.append({
                "id": f"M-{uuid.uuid4().hex[:10].upper()}",
                "mcc": mcc_code,
                "mcc_desc": mcc_desc,
                "name": fake.company(),
                "city": fake.city(),
                "country": fake.country_code(representation="alpha-2"),
                "currency": fake.currency_code()
            })
        return merchants

class TerminalEngine:
    def generate_terminals(self, merchants, max_terminals_per_merchant=5):
        terminals = []
        for merchant in merchants:
            for _ in range(random.randint(1, max_terminals_per_merchant)):
                terminals.append({
                    "id": f"T-{uuid.uuid4().hex[:8].upper()}",
                    "merchant_id": merchant["id"]
                })
        return terminals

# ==========================================
# 3. Behavioral Simulation Engine
# ==========================================
class BehavioralEngine:
    def __init__(self, translator):
        self.translator = translator

    def simulate(self, cardholders, merchants, terminals, num_transactions, fraud_rate=0.05):
        transactions = []
        current_time = datetime.now()

        for _ in range(num_transactions):
            cardholder = random.choice(cardholders)
            terminal = random.choice(terminals)
            merchant = next(m for m in merchants if m["id"] == terminal["merchant_id"])
            
            is_fraud = random.random() < fraud_rate
            
            # Stochastic value processes[cite: 1]
            if is_fraud:
                amount = round(random.uniform(500.0, 10000.0), 2)
            else:
                amount = round(random.expovariate(1/150.0), 2) + 1.0 

            time_offset = timedelta(minutes=random.randint(1, 120))
            current_time += time_offset

            tx_record = self.translator.format_transaction(
                cardholder, merchant, terminal, amount, is_fraud, current_time
            )
            transactions.append(tx_record)
            
        return transactions

# ==========================================
# 5. Serialization & Streaming Layer
# ==========================================
class DataSerializer:
    @staticmethod
    def to_json(data, filename):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"[*] Successfully wrote {len(data)} records to {filename}")

    @staticmethod
    def to_csv(data, filename):
        if not data:
            return
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)
        print(f"[*] Successfully wrote {len(data)} records to {filename}")

# ==========================================
# 1. Configuration & CLI Layer
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Synthetic Authorization Generator (SAG)")
    parser.add_argument("--count", type=int, default=100, help="Number of transactions to generate")
    parser.add_argument("--users", type=int, default=20, help="Virtual population size")
    parser.add_argument("--merchants", type=int, default=10, help="Merchant database size")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--output", type=str, default="output.json", help="Output filename")
    
    args = parser.parse_args()

    translator = ISO8583Translator()
    pop_engine = PopulationEngine(translator)
    merch_engine = MerchantEngine()
    term_engine = TerminalEngine()
    behavior_engine = BehavioralEngine(translator)

    print("[*] Initializing Virtual World with Dynamic Data...")
    cardholders = pop_engine.generate_cardholders(args.users)
    merchants = merch_engine.generate_merchants(args.merchants)
    terminals = term_engine.generate_terminals(merchants)

    print(f"[*] Simulating {args.count} transactions...")
    transactions = behavior_engine.simulate(cardholders, merchants, terminals, args.count)

    print(f"[*] Serializing output to {args.format.upper()}...")
    if args.format == "json":
        DataSerializer.to_json(transactions, args.output)
    else:
        DataSerializer.to_csv(transactions, args.output)

if __name__ == "__main__":
    main()