from pydantic import BaseModel, Field
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Cardholder:
    id: str
    pan: str
    account_number: str
    account_status: str
    name: str
    email: str
    address: str
    creation_date: datetime
    password_change_date: datetime
    suspicious_history: bool
    transaction_history: list
    device_id: str
    ip_address: str
    user_agent: str
    screen_height: int
    screen_width: int
    color_depth: int
    timezone: str
    kyc_level: str = "standard"
    tenure_days: int = 0
    prior_chargeback_count_30d: int = 0


@dataclass
class Merchant:
    id: str
    mcc: str
    mcc_desc: str
    name: str
    city: str
    delivery_type: str
    inventory_sample: list
    merchant_risk_tier: str = "low"
    merchant_chargeback_ratio_90d: float = 0.0
    merchant_onboard_age_days: int = 365


@dataclass
class Terminal:
    id: str
    merchant_id: str


class Transaction(BaseModel):
    transaction_id: str
    schema_version: str
    generator_version: str
    MTI: str
    Timestamp: str
    DE002_PAN: str
    DE003_ProcessingCode: str
    DE004_Amount: str
    DE022_POSEntryMode: str
    DE025_POSCondition: str
    DE038_AuthCode: str
    DE039_ResponseCode: str
    DE041_TerminalID: str
    DE042_MerchantID: str
    DE043_MerchantLocation: str
    Cust_ID: str
    Cust_Name: str
    Cust_Email: str
    Cust_Address: str
    Account_Number: str
    Account_Status: str
    Order_Amount_Micros: int
    addressMatch: str
    Account_Risk: dict
    Device_Browser_Telemetry: dict
    Item_Metadata: dict
    Authentication_3DS2: dict
    Is_Fraud: bool
    # Additional fields
    customer_id: str = ""
    kyc_level: str = ""
    tenure_days: int = 0
    prior_chargeback_count_30d: int = 0
    card_brand: str = ""
    card_product: str = ""
    issuer_bin: str = ""
    card_expiry_month: int = 0
    card_expiry_year: int = 0
    cvv_result: str = ""
    avs_result: str = ""
    tokenized_pan: bool = False
    network_token_type: str = ""
    transaction_id_network: str = ""
    retrieval_reference_number: str = ""
    authorization_lifecycle: str = ""
    installment_count: int = 0
    tip_amount: float = 0.0
    tax_amount: float = 0.0
    shipping_amount: float = 0.0
    merchant_country: str = ""
    card_issuing_country: str = ""
    geo_distance: float = 0.0
    currency_conversion_rate: float = 1.0
    original_amount: float = 0.0
    device_trust_score: float = 0.0
    proxy_vpn_tor_flag: bool = False
    ip_risk_score: float = 0.0
    device_first_seen_at: str = ""
    device_age_days: int = 0
    cookie_age_days: int = 0
    sim_swap_recent_flag: bool = False
    txn_count_1h: int = 0
    txn_count_24h: int = 0
    txn_count_7d: int = 0
    amount_sum_1h: float = 0.0
    amount_sum_24h: float = 0.0
    amount_sum_7d: float = 0.0
    distinct_merchants_24h: int = 0
    distinct_cards_per_device_24h: int = 0
    failed_auth_count_24h: int = 0
    time_since_last_txn_sec: int = 0
    mcc_risk_score: float = 0.0
    is_marketplace_submerchant: bool = False
    submerchant_id: str = ""