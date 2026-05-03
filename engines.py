import random
import uuid
from datetime import datetime, timedelta, timezone
from faker import Faker
from models import Cardholder, Merchant, Terminal

# Initialize Faker for realistic PII generation
fake = Faker(['en_US'])


class PopulationEngine:
    def __init__(self, translator):
        self.translator = translator

    def generate_cardholders(self, count):
        cardholders = []
        now = datetime.now(timezone.utc)
        for _ in range(count):
            is_bot = random.random() < 0.05
            tenure_days = random.randint(0, 365)
            creation_date = now - timedelta(days=tenure_days)
            cardholders.append(Cardholder(
                id=f"CH-{random.randint(10000, 99999)}",
                pan=self.translator.generate_luhn(),
                account_number=f"ACCT-{random.randint(100000000, 999999999)}",
                account_status=random.choice(["active", "active", "active", "frozen"]),
                name=fake.name(),
                email=fake.free_email(),
                address=fake.street_address(),
                creation_date=creation_date,
                password_change_date=now - timedelta(days=random.randint(0, 100)),
                suspicious_history=is_bot,
                transaction_history=[],
                device_id=str(uuid.uuid4()),
                ip_address=fake.ipv4(),
                user_agent=fake.user_agent() if not is_bot else "curl/7.68.0",
                screen_height=random.choice([1080, 2532, 1920]) if not is_bot else 600,
                screen_width=random.choice([1920, 1170, 1080]) if not is_bot else 800,
                color_depth=24 if not is_bot else 8,
                timezone=fake.timezone(),
                kyc_level=random.choice(["basic", "standard", "premium"]),
                tenure_days=tenure_days,
                prior_chargeback_count_30d=random.randint(0, 2)
            ))
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

            merchants.append(Merchant(
                id=f"M-{random.randint(100000, 999999)}",
                mcc=mcc_code,
                mcc_desc=mcc_data["desc"],
                name=fake.company(),
                city=fake.city(),
                delivery_type=mcc_data["delivery"],
                inventory_sample=inventory,
                merchant_risk_tier=random.choice(["low", "medium", "high"]),
                merchant_chargeback_ratio_90d=random.uniform(0, 0.05),
                merchant_onboard_age_days=random.randint(30, 365*2)
            ))
        return merchants


class TerminalEngine:
    def generate_terminals(self, merchants, terminals_per_merchant=2):
        terminals = []
        for merchant in merchants:
            for _ in range(random.randint(1, terminals_per_merchant)):
                terminals.append(Terminal(
                    id=f"T{random.randint(1000000, 9999999)}",
                    merchant_id=merchant.id,
                ))
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
            merchant = next(m for m in merchants if m.id == terminal.merchant_id)

            is_fraud = random.random() < fraud_rate
            if is_fraud:
                amount = round(random.uniform(500.0, 5000.0), 2)
                time_offset = timedelta(minutes=random.randint(1, 5))
            else:
                amount = round(random.expovariate(1 / 50.0), 2) + 1.0
                time_offset = timedelta(minutes=random.randint(60, 1440))

            current_time += time_offset
            cardholder.transaction_history.append(current_time)
            velocity_24h = sum(1 for t in cardholder.transaction_history if (current_time - t) <= timedelta(hours=24))

            tx_record = self.translator.format_transaction(
                cardholder.__dict__, merchant.__dict__, terminal.__dict__, amount, is_fraud, current_time, velocity_24h
            )
            transactions.append(tx_record)

        return transactions