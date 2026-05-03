import argparse
import json
import csv
import random
from datetime import datetime, timedelta

# ==========================================
# 4. ISO 8583 Translation Layer
# ==========================================
class ISO8583Translator:
    """Formats logical events into specific MTIs and data elements (DE)."""
    
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

    def format_transaction(self, cardholder, merchant, amount, is_fraud, timestamp):
        """Translates simulated data into ISO 8583 fields[cite: 1]."""
        # MTI: 0100 for Authorization Request[cite: 1]
        mti = "0100" 
        
        # DE 3: Processing Code (e.g., 000000 for standard purchase)[cite: 1]
        de3_processing_code = "000000" 
        
        # DE 4: Amount in smallest currency unit (12 digits)[cite: 1]
        de4_amount = f"{int(amount * 100):012d}" 
        
        # DE 43: Merchant Location (40 chars)[cite: 1]
        de43_location = f"{merchant['name'][:22]:<22}{merchant['city'][:13]:<13}{merchant['country'][:2]:<2}"
        
        # DE 48/52/55: Mock Tokenization and Chip/PIN metadata for risk testing[cite: 1]
        de48_token = f"PAR-{random.randint(1000, 9999)}"
        
        return {
            "MTI": mti,
            "DE002_PAN": cardholder["pan"],
            "DE003_ProcessingCode": de3_processing_code,
            "DE004_Amount": de4_amount,
            "DE043_MerchantLocation": de43_location,
            "DE048_TokenData": de48_token,
            "Timestamp": timestamp.isoformat(),
            "Is_Fraud": is_fraud # Retained for dashboard testing[cite: 1]
        }

# ==========================================
# 2. Population & Merchant Engine
# ==========================================
class PopulationEngine:
    """Generates a virtual population with permanent attributes[cite: 1]."""
    def __init__(self, translator):
        self.translator = translator

    def generate_cardholders(self, count):
        cardholders = []
        for _ in range(count):
            cardholders.append({
                "id": f"CH-{random.randint(10000, 99999)}",
                "pan": self.translator.generate_luhn(),
                "age": int(random.gauss(40, 15)), # Gaussian distribution for demographics[cite: 1]
                "income": round(random.lognormvariate(10.5, 0.5), 2) # Log-Normal distribution[cite: 1]
            })
        return cardholders

class MerchantEngine:
    """Maintains a database linking MCCs to specific IDs and locations[cite: 1]."""
    def generate_merchants(self, count):
        mccs = ["5411", "5812", "5541", "5999"] # Groceries, Restaurants, Gas, Misc
        cities = ["San Juan", "New York", "London", "Miami"]
        merchants = []
        for _ in range(count):
            merchants.append({
                "id": f"M-{random.randint(1000, 9999)}",
                "mcc": random.choice(mccs),
                "name": f"Merchant {random.randint(100, 999)}",
                "city": random.choice(cities),
                "country": "US"
            })
        return merchants

# ==========================================
# 3. Behavioral Simulation Engine
# ==========================================
class BehavioralEngine:
    """Models human behavior and malicious activity using stochastic processes[cite: 1]."""
    def __init__(self, translator):
        self.translator = translator

    def simulate(self, cardholders, merchants, num_transactions, fraud_rate=0.05):
        transactions = []
        current_time = datetime.now()

        for _ in range(num_transactions):
            cardholder = random.choice(cardholders)
            merchant = random.choice(merchants)
            
            # Stochastic determination of monetary value ($A_t$)[cite: 1]
            is_fraud = random.random() < fraud_rate
            if is_fraud:
                # Fraud Injection: Velocity attacks / High amounts[cite: 1]
                amount = round(random.uniform(500.0, 5000.0), 2)
            else:
                # Normal spending states[cite: 1]
                amount = round(random.expovariate(1/50.0), 2) + 1.0 

            # Temporal state machine increment (mocking time progression)[cite: 1]
            time_offset = timedelta(minutes=random.randint(1, 60))
            current_time += time_offset

            tx_record = self.translator.format_transaction(
                cardholder, merchant, amount, is_fraud, current_time
            )
            transactions.append(tx_record)
            
        return transactions

# ==========================================
# 5. Serialization & Streaming Layer
# ==========================================
class DataSerializer:
    """Writes records to disk in JSON or CSV formats[cite: 1]."""
    
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
        with open(filename, 'w', newline='') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)
        print(f"[*] Successfully wrote {len(data)} records to {filename}")

# ==========================================
# 1. Configuration & CLI Layer
# ==========================================
def main():
    """Manages user inputs and ties the modular pipeline together[cite: 1]."""
    parser = argparse.ArgumentParser(description="Synthetic Authorization Generator (SAG)")
    parser.add_argument("--count", type=int, default=100, help="Number of transactions to generate")
    parser.add_argument("--users", type=int, default=20, help="Virtual population size")
    parser.add_argument("--merchants", type=int, default=10, help="Merchant database size")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output serialization format")
    parser.add_argument("--output", type=str, default="output.json", help="Output filename")
    
    args = parser.parse_args()

    # Initialize Modules
    translator = ISO8583Translator()
    pop_engine = PopulationEngine(translator)
    merch_engine = MerchantEngine()
    behavior_engine = BehavioralEngine(translator)

    print("[*] Initializing Virtual World...")
    cardholders = pop_engine.generate_cardholders(args.users)
    merchants = merch_engine.generate_merchants(args.merchants)

    print(f"[*] Simulating {args.count} transactions...")
    transactions = behavior_engine.simulate(cardholders, merchants, args.count)

    print(f"[*] Serializing output to {args.format.upper()}...")
    if args.format == "json":
        DataSerializer.to_json(transactions, args.output)
    else:
        DataSerializer.to_csv(transactions, args.output)

if __name__ == "__main__":
    main()