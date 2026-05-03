import argparse
import json
import random
import string
import uuid
import os
from datetime import datetime, timedelta, timezone
from faker import Faker

# Initialize Faker for realistic PII generation
fake = Faker(['en_US'])


class ModernTransactionTranslator:
    """Formats logical events incorporating ISO 8583, ISO 20022, 3DS2, and Sift fields."""

    def __init__(self, mask_pan=False, mask_email=False, tokenize_customer=False):
        self.mask_pan = mask_pan
        self.mask_email = mask_email
        self.tokenize_customer = tokenize_customer

    @staticmethod
    def generate_luhn(length=16):
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

    @staticmethod
    def mask_pan_value(pan):
        return f"{pan[:6]}{'*' * 6}{pan[-4:]}"

    @staticmethod
    def mask_email_value(email):
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[:2] + "*" * (len(local) - 2)
        return f"{masked_local}@{domain}"

    def format_transaction(self, cardholder, merchant, terminal, amount, is_fraud, timestamp, velocity_24h):
        mti = "0100"
        de3_processing_code = "000000"
        amount_micros = int(amount * 1000000)
        de4_amount = f"{int(amount * 100):012d}"

        de22_pos_entry_mode = random.choice(["051", "071", "010", "801"])
        de25_pos_condition_code = "51" if merchant['mcc'] == "5541" else "00"

        de39_response_code = random.choice(["05", "51", "54", "55", "59"]) if is_fraud else "00"
        de38_auth_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) if de39_response_code == "00" else ""

        account_age_days = (timestamp - cardholder['creation_date']).days
        acct_age_ind = "01" if account_age_days < 1 else "02" if account_age_days < 60 else "05"

        address_match = "Y" if random.random() > 0.1 else "N"
        if is_fraud and random.random() > 0.4:
            address_match = "N"

        pan_output = self.mask_pan_value(cardholder["pan"]) if self.mask_pan else cardholder["pan"]
        email_output = self.mask_email_value(cardholder["email"]) if self.mask_email else cardholder["email"]
        customer_id = f"TOK-{uuid.uuid5(uuid.NAMESPACE_DNS, cardholder['id']).hex[:16]}" if self.tokenize_customer else cardholder["id"]

        return {
            "transaction_id": str(uuid.uuid4()),
            "schema_version": "1.1.0",
            "generator_version": "synthraGen-1.1",
            "MTI": mti,
            "Timestamp": timestamp.isoformat(),
            "DE002_PAN": pan_output,
            "DE003_ProcessingCode": de3_processing_code,
            "DE004_Amount": de4_amount,
            "DE022_POSEntryMode": de22_pos_entry_mode,
            "DE025_POSCondition": de25_pos_condition_code,
            "DE038_AuthCode": de38_auth_code,
            "DE039_ResponseCode": de39_response_code,
            "DE041_TerminalID": terminal['id'],
            "DE042_MerchantID": merchant['id'],
            "DE043_MerchantLocation": f"{merchant['name'][:22]:<22}{merchant['city'][:13]:<13}US",
            "Cust_ID": customer_id,
            "Cust_Name": cardholder["name"],
            "Cust_Email": email_output,
            "Cust_Address": cardholder["address"],
            "Account_Number": cardholder["account_number"],
            "Account_Status": cardholder["account_status"],
            "Order_Amount_Micros": amount_micros,
            "addressMatch": address_match,
            "Account_Risk": {
                "acctAgeInd": acct_age_ind,
                "acctChangeInd": "04" if (timestamp - cardholder['password_change_date']).days < 1 else "01",
                "suspiciousAccActivity": cardholder['suspicious_history'],
                "txnActivityDay": velocity_24h,
            },
            "Device_Browser_Telemetry": {
                "ipAddress": cardholder["ip_address"],
                "identifierForVendor": cardholder["device_id"],
                "browserDetails": {
                    "userAgent": cardholder["user_agent"],
                    "screenHeight": cardholder["screen_height"],
                    "screenWidth": cardholder["screen_width"],
                    "colorDepth": cardholder["color_depth"],
                    "timeZone": cardholder["timezone"]
                }
            },
            "Item_Metadata": {
                "items": merchant['inventory_sample'],
                "shipping_method": merchant['delivery_type'],
                "promotions": [] if not is_fraud else [{"promo_code": "NEWUSER50"}]
            },
            "Authentication_3DS2": {
                "transactionStatus": "Y" if de39_response_code == "00" else random.choice(["N", "U", "R"]),
                "threeDSRequestorChallengeInd": "01" if is_fraud else "05"
            },
            "Is_Fraud": is_fraud
        }


class PopulationEngine:
    def __init__(self, translator):
        self.translator = translator

    def generate_cardholders(self, count):
        cardholders = []
        now = datetime.now(timezone.utc)
        for _ in range(count):
            is_bot = random.random() < 0.05
            cardholders.append({
                "id": f"CH-{random.randint(10000, 99999)}",
                "pan": self.translator.generate_luhn(),
                "account_number": f"ACCT-{random.randint(100000000, 999999999)}",
                "account_status": random.choice(["active", "active", "active", "frozen"]),
                "name": fake.name(),
                "email": fake.free_email(),
                "address": fake.street_address(),
                "creation_date": now - timedelta(days=random.randint(0, 365)),
                "password_change_date": now - timedelta(days=random.randint(0, 100)),
                "suspicious_history": is_bot,
                "transaction_history": [],
                "device_id": str(uuid.uuid4()),
                "ip_address": fake.ipv4(),
                "user_agent": fake.user_agent() if not is_bot else "curl/7.68.0",
                "screen_height": random.choice([1080, 2532, 1920]) if not is_bot else 600,
                "screen_width": random.choice([1920, 1170, 1080]) if not is_bot else 800,
                "color_depth": 24 if not is_bot else 8,
                "timezone": fake.timezone()
            })
        return cardholders


class MerchantEngine:
    def __init__(self, mcc_mapping=None):
        self.mccs = mcc_mapping or {
            "5411": {"desc": "Groceries", "delivery": "$physical"},
            "5812": {"desc": "Restaurants", "delivery": "$physical"},
            "5541": {"desc": "Gas Stations", "delivery": "$physical"},
            "5999": {"desc": "Misc Retail", "delivery": "$physical"},
            "4511": {"desc": "Airlines", "delivery": "$electronic"},
            "5816": {"desc": "Digital Goods", "delivery": "$electronic"},
            "5732": {"desc": "Electronics Stores", "delivery": "$physical"},
            "4121": {"desc": "Taxicabs/Rideshare", "delivery": "$electronic"},
            "7011": {"desc": "Hotels/Lodging", "delivery": "$physical"}
        }

    def generate_merchants(self, count):
        merchants = []
        mcc_keys = list(self.mccs.keys())

        for _ in range(count):
            mcc_code = random.choice(mcc_keys)
            mcc_data = self.mccs[mcc_code]
            inventory = [{
                "item_id": f"SKU-{random.randint(1000,9999)}",
                "brand": fake.company(),
                "quantity": random.randint(1, 3)
            } for _ in range(random.randint(1, 4))]

            merchants.append({
                "id": f"M-{random.randint(100000, 999999)}",
                "mcc": mcc_code,
                "mcc_desc": mcc_data["desc"],
                "name": fake.company(),
                "city": fake.city(),
                "delivery_type": mcc_data["delivery"],
                "inventory_sample": inventory
            })
        return merchants


class TerminalEngine:
    def generate_terminals(self, merchants, terminals_per_merchant=2):
        terminals = []
        for merchant in merchants:
            for _ in range(random.randint(1, terminals_per_merchant)):
                terminals.append({
                    "id": f"T{random.randint(1000000, 9999999)}",
                    "merchant_id": merchant["id"],
                })
        return terminals


class BehavioralEngine:
    def __init__(self, translator):
        self.translator = translator

    def simulate(self, cardholders, merchants, terminals, num_transactions, fraud_rate=0.05):
        transactions = []
        current_time = datetime.now(timezone.utc)

        for _ in range(num_transactions):
            cardholder = random.choice(cardholders)
            terminal = random.choice(terminals)
            merchant = next(m for m in merchants if m["id"] == terminal["merchant_id"])

            is_fraud = random.random() < fraud_rate
            if is_fraud:
                amount = round(random.uniform(500.0, 5000.0), 2)
                time_offset = timedelta(minutes=random.randint(1, 5))
            else:
                amount = round(random.expovariate(1 / 50.0), 2) + 1.0
                time_offset = timedelta(minutes=random.randint(60, 1440))

            current_time += time_offset
            cardholder['transaction_history'].append(current_time)
            velocity_24h = sum(1 for t in cardholder['transaction_history'] if (current_time - t) <= timedelta(hours=24))

            tx_record = self.translator.format_transaction(
                cardholder, merchant, terminal, amount, is_fraud, current_time, velocity_24h
            )
            transactions.append(tx_record)

        return transactions


class DataSerializer:
    @staticmethod
    def to_json(data, filename):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"[*] Successfully wrote {len(data)} enhanced records to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Advanced Synthetic Transaction Generator (ASTG)")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--merchants", type=int, default=10)
    parser.add_argument("--output", type=str, default="output.json")
    parser.add_argument("--mcc-file", type=str, default=None, help="Path to a JSON file containing custom MCC mappings")
    parser.add_argument("--seed", type=int, default=None, help="Optional deterministic seed")
    parser.add_argument("--mask-pan", action="store_true", help="Mask PAN in output")
    parser.add_argument("--mask-email", action="store_true", help="Mask customer email in output")
    parser.add_argument("--tokenize-customer", action="store_true", help="Emit tokenized customer ID")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        Faker.seed(args.seed)

    custom_mccs = None
    if args.mcc_file and os.path.exists(args.mcc_file):
        print(f"[*] Loading dynamic MCC configuration from {args.mcc_file}...")
        with open(args.mcc_file, 'r') as f:
            custom_mccs = json.load(f)

    translator = ModernTransactionTranslator(
        mask_pan=args.mask_pan,
        mask_email=args.mask_email,
        tokenize_customer=args.tokenize_customer,
    )
    pop_engine = PopulationEngine(translator)
    merch_engine = MerchantEngine(mcc_mapping=custom_mccs)
    term_engine = TerminalEngine()
    behavior_engine = BehavioralEngine(translator)

    print("[*] Initializing State-Based Virtual World...")
    cardholders = pop_engine.generate_cardholders(args.users)
    merchants = merch_engine.generate_merchants(args.merchants)
    terminals = term_engine.generate_terminals(merchants)

    print(f"[*] Simulating {args.count} contextual transactions...")
    transactions = behavior_engine.simulate(cardholders, merchants, terminals, args.count)

    print("[*] Serializing complex JSON output...")
    DataSerializer.to_json(transactions, args.output)


if __name__ == "__main__":
    main()
