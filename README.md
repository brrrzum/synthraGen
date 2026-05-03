# synthraGen

Advanced Synthetic Transaction Generator for payment data simulation.

## Features

- Generates realistic synthetic payment transactions
- Includes fraud simulation with configurable rates
- Supports PII masking and tokenization by default
- JSON Schema validation for output consistency
- Configurable MCC mappings
- Deterministic seeding for reproducibility
- Extensive datapoints for ML model training

## Installation

Requires Python 3.8+ and dependencies:
- faker
- pydantic

Install dependencies:
```bash
pip install faker pydantic
```

## Usage

Run the generator:
```bash
python sag.py --count 100 --users 20 --merchants 10 --output transactions.json
```

Options:
- `--count`: Number of transactions to generate (default: 100)
- `--users`: Number of cardholders (default: 20)
- `--merchants`: Number of merchants (default: 10)
- `--output`: Output file (default: output.json)
- `--mcc-file`: Custom MCC configuration file
- `--seed`: Random seed for reproducibility
- `--mask-pan`: Mask PAN (default: True)
- `--mask-email`: Mask email (default: True)
- `--tokenize-customer`: Tokenize customer ID (default: True)

## Configuration

MCC mappings can be customized via JSON file (see mcc_config.json).

## Testing

Run tests:
```bash
python -m unittest test_sag.py
```

## Troubleshooting

- Ensure all dependencies are installed
- Check file paths for config files
- Use --seed for reproducible results