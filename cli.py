import argparse
import json
import os
import random
from faker import Faker
from translator import ModernTransactionTranslator
from engines import PopulationEngine, MerchantEngine, TerminalEngine, BehavioralEngine
from writers import DataSerializer

# Initialize Faker
fake = Faker(['en_US'])


def main():
    parser = argparse.ArgumentParser(description="Advanced Synthetic Transaction Generator (ASTG)")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--merchants", type=int, default=10)
    parser.add_argument("--output", type=str, default="output.json")
    parser.add_argument("--mcc-file", type=str, default=None, help="Path to a JSON file containing custom MCC mappings")
    parser.add_argument("--seed", type=int, default=None, help="Optional deterministic seed")
    parser.add_argument("--mask-pan", action="store_true", default=True, help="Mask PAN in output")
    parser.add_argument("--mask-email", action="store_true", default=True, help="Mask customer email in output")
    parser.add_argument("--tokenize-customer", action="store_true", default=True, help="Emit tokenized customer ID")

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