import random
import string
import uuid
from datetime import datetime, timedelta
from models import Transaction


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
            if i % 2 == 0:  # For 15 digits, double even indices in reversed
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

        # Condition response code on risk features
        base_response = "00"
        if is_fraud:
            if velocity_24h > 5:
                base_response = random.choice(["05", "51", "54"])
            else:
                base_response = random.choice(["05", "51", "54", "55", "59"])
        de39_response_code = base_response
        de38_auth_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) if de39_response_code == "00" else ""

        account_age_days = (timestamp - cardholder['creation_date']).days
        acct_age_ind = "01" if account_age_days < 1 else "02" if account_age_days < 60 else "05"

        address_match = "Y" if random.random() > 0.1 else "N"
        if is_fraud and random.random() > 0.4:
            address_match = "N"

        pan_output = self.mask_pan_value(cardholder["pan"]) if self.mask_pan else cardholder["pan"]
        email_output = self.mask_email_value(cardholder["email"]) if self.mask_email else cardholder["email"]
        customer_id = f"TOK-{uuid.uuid5(uuid.NAMESPACE_DNS, cardholder['id']).hex[:16]}" if self.tokenize_customer else cardholder["id"]

        # Additional fields
        card_brand = random.choice(["Visa", "Mastercard", "Amex"])
        card_product = random.choice(["debit", "credit", "prepaid"])
        issuer_bin = cardholder["pan"][:6]
        expiry_month = random.randint(1, 12)
        expiry_year = timestamp.year + random.randint(1, 5)
        cvv_result = random.choice(["M", "N", "P", "U"])
        avs_result = random.choice(["Y", "N", "A", "U", "Z"])
        tokenized_pan = self.mask_pan
        network_token_type = "DPAN" if tokenized_pan else ""
        transaction_id_network = str(uuid.uuid4())
        retrieval_ref = ''.join(random.choices(string.digits, k=12))
        auth_lifecycle = "auth"
        installment_count = 0
        tip_amount = 0.0
        tax_amount = amount * 0.08
        shipping_amount = random.uniform(0, 10)
        merchant_country = "US"
        issuing_country = "US"
        geo_distance = random.uniform(0, 1000)
        conversion_rate = 1.0
        original_amount = amount
        device_trust_score = random.uniform(0, 1)
        proxy_flag = random.random() < 0.05
        ip_risk_score = random.uniform(0, 1)
        device_first_seen = (timestamp - timedelta(days=random.randint(0, 365))).isoformat()
        device_age_days = random.randint(0, 365)
        cookie_age_days = random.randint(0, 30)
        sim_swap_flag = random.random() < 0.01
        txn_count_1h = velocity_24h // 24  # approx
        txn_count_24h = velocity_24h
        txn_count_7d = velocity_24h * 7
        amount_sum_1h = amount * txn_count_1h
        amount_sum_24h = amount * txn_count_24h
        amount_sum_7d = amount * txn_count_7d
        distinct_merchants_24h = random.randint(1, 5)
        distinct_cards_per_device_24h = 1
        failed_auth_count_24h = random.randint(0, 3)
        time_since_last_txn = random.randint(0, 86400)
        mcc_risk_score = random.uniform(0, 1)
        is_marketplace = random.random() < 0.1
        submerchant_id = f"SUB-{random.randint(1000,9999)}" if is_marketplace else ""

        return Transaction(
            transaction_id=str(uuid.uuid4()),
            schema_version="1.1.0",
            generator_version="synthraGen-1.1",
            MTI=mti,
            Timestamp=timestamp.isoformat(),
            DE002_PAN=pan_output,
            DE003_ProcessingCode=de3_processing_code,
            DE004_Amount=de4_amount,
            DE022_POSEntryMode=de22_pos_entry_mode,
            DE025_POSCondition=de25_pos_condition_code,
            DE038_AuthCode=de38_auth_code,
            DE039_ResponseCode=de39_response_code,
            DE041_TerminalID=terminal['id'],
            DE042_MerchantID=merchant['id'],
            DE043_MerchantLocation=f"{merchant['name'][:22]:<22}{merchant['city'][:13]:<13}US",
            Cust_ID=customer_id,
            Cust_Name=cardholder["name"],
            Cust_Email=email_output,
            Cust_Address=cardholder["address"],
            Account_Number=cardholder["account_number"],
            Account_Status=cardholder["account_status"],
            Order_Amount_Micros=amount_micros,
            addressMatch=address_match,
            Account_Risk={
                "acctAgeInd": acct_age_ind,
                "acctChangeInd": "04" if (timestamp - cardholder['password_change_date']).days < 1 else "01",
                "suspiciousAccActivity": cardholder['suspicious_history'],
                "txnActivityDay": velocity_24h,
            },
            Device_Browser_Telemetry={
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
            Item_Metadata={
                "items": merchant['inventory_sample'],
                "shipping_method": merchant['delivery_type'],
                "promotions": [] if not is_fraud else [{"promo_code": "NEWUSER50"}]
            },
            Authentication_3DS2={
                "transactionStatus": "Y" if de39_response_code == "00" else random.choice(["N", "U", "R"]),
                "threeDSRequestorChallengeInd": "01" if is_fraud else "05"
            },
            Is_Fraud=is_fraud,
            customer_id=cardholder["id"],
            kyc_level=cardholder.get("kyc_level", "standard"),
            tenure_days=account_age_days,
            prior_chargeback_count_30d=cardholder.get("prior_chargeback_count_30d", 0),
            card_brand=card_brand,
            card_product=card_product,
            issuer_bin=issuer_bin,
            card_expiry_month=expiry_month,
            card_expiry_year=expiry_year,
            cvv_result=cvv_result,
            avs_result=avs_result,
            tokenized_pan=tokenized_pan,
            network_token_type=network_token_type,
            transaction_id_network=transaction_id_network,
            retrieval_reference_number=retrieval_ref,
            authorization_lifecycle=auth_lifecycle,
            installment_count=installment_count,
            tip_amount=tip_amount,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            merchant_country=merchant_country,
            card_issuing_country=issuing_country,
            geo_distance=geo_distance,
            currency_conversion_rate=conversion_rate,
            original_amount=original_amount,
            device_trust_score=device_trust_score,
            proxy_vpn_tor_flag=proxy_flag,
            ip_risk_score=ip_risk_score,
            device_first_seen_at=device_first_seen,
            device_age_days=device_age_days,
            cookie_age_days=cookie_age_days,
            sim_swap_recent_flag=sim_swap_flag,
            txn_count_1h=txn_count_1h,
            txn_count_24h=txn_count_24h,
            txn_count_7d=txn_count_7d,
            amount_sum_1h=amount_sum_1h,
            amount_sum_24h=amount_sum_24h,
            amount_sum_7d=amount_sum_7d,
            distinct_merchants_24h=distinct_merchants_24h,
            distinct_cards_per_device_24h=distinct_cards_per_device_24h,
            failed_auth_count_24h=failed_auth_count_24h,
            time_since_last_txn_sec=time_since_last_txn,
            mcc_risk_score=mcc_risk_score,
            is_marketplace_submerchant=is_marketplace,
            submerchant_id=submerchant_id
        )