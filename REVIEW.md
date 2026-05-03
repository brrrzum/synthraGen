# Code Evaluation and Improvement Suggestions

## High-priority fixes

1. **PII masking and synthetic-data safety**
   - The generator emits full PAN, full name, full email, and address in clear text. Even for synthetic datasets, downstream systems often require PCI-safe formats.
   - Suggestion: add flags for `--mask-pan`, `--mask-email`, `--tokenize-customer`, and default to masked output.

2. **Reproducibility controls**
   - Data generation currently uses `random` and `faker` without deterministic seeding.
   - Suggestion: add `--seed` and apply to both `random.seed(seed)` and `Faker.seed(seed)`.

3. **Schema consistency and validation**
   - Nested structures are rich, but there is no explicit schema/validator.
   - Suggestion: define JSON Schema (or Pydantic models) and validate each record before writing files.

4. **Time consistency bug risk**
   - Cardholder lifecycle fields are anchored on `datetime.now()` while generated transaction timestamps can drift without timezone normalization.
   - Suggestion: standardize on UTC-aware timestamps and include a single event clock source.

5. **Response and fraud logic realism**
   - Fraud/non-fraud mapping currently uses simple random response codes.
   - Suggestion: condition response code distributions on risk features (velocity spikes, AVS mismatch, bot fingerprint, MCC risk).

## Medium-priority engineering improvements

1. **Split monolithic file**
   - `sag.py` mixes models, generation logic, formatting, and IO.
   - Suggestion: split into `models.py`, `engines.py`, `translator.py`, `writers.py`, `cli.py`.

2. **Typed models + docs**
   - Use dataclasses or Pydantic with type hints to improve maintainability and editor support.

3. **Test coverage**
   - Add tests for:
     - Luhn correctness
     - amount micros/DE004 conversions
     - DE043 fixed-width formatting
     - fraud-label distribution bounds

4. **Config externalization**
   - MCC map and fraud probabilities should be in config (YAML/JSON), not hardcoded.

5. **Output contracts**
   - Version the output schema (`schema_version`) and include `generator_version` metadata in every record.

## Suggested missing datapoints

Below are likely missing payment/fraud features that improve model and rule performance.

### Account and customer attributes
- `account_number` (bank/DDA surrogate tokenized)
- `customer_id` stable cross-session key
- `account_status` (active, frozen, closed)
- `kyc_level` / verification tier
- `tenure_days`
- `prior_chargeback_count_30d/90d`
- `linked_cards_count`

### Card and instrument metadata
- `card_brand` (Visa/Mastercard/etc.)
- `card_product` (debit/credit/prepaid/commercial)
- `issuer_bin` / `iin`
- `card_expiry_month`, `card_expiry_year`
- `cvv_result` (M/N/P/U)
- `avs_result` (Y/N/A/U/Z)
- `tokenized_pan` flag + `network_token_type`

### Transaction enrichment
- `transaction_id` (network-unique)
- `retrieval_reference_number` / `stan`
- `authorization_lifecycle` (auth, reversal, capture, refund)
- `installment_count`
- `tip_amount`, `tax_amount`, `shipping_amount`
- `merchant_country`, `card_issuing_country`, and geo-distance
- `currency_conversion_rate` and `original_amount` for FX flows

### Device / network telemetry
- `device_trust_score`
- `proxy_vpn_tor_flag`
- `ip_risk_score`
- `device_first_seen_at` / `device_age_days`
- `cookie_age_days`
- `sim_swap_recent_flag` (if mobile context)

### Behavioral and velocity features
- `txn_count_1h/24h/7d`
- `amount_sum_1h/24h/7d`
- `distinct_merchants_24h`
- `distinct_cards_per_device_24h`
- `failed_auth_count_24h`
- `time_since_last_txn_sec`

### Merchant-side risk signals
- `merchant_risk_tier`
- `merchant_chargeback_ratio_90d`
- `merchant_onboard_age_days`
- `mcc_risk_score`
- `is_marketplace_submerchant` and `submerchant_id`

### 3DS2/EMVCo additional fields
- `threeDSRequestorAuthenticationInd`
- `threeDSCompInd`
- `transType`
- `messageCategory`
- `sdkAppID` / `sdkTransID`
- `acsTransID`
- `eci` and `cavv`

## Quick roadmap

1. Add deterministic seed + masking defaults.
2. Introduce schema models and validation.
3. Add missing high-value datapoints from sections above.
4. Add pytest suite and CI checks.
