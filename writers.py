import json
from models import Transaction


class DataSerializer:
    @staticmethod
    def to_json(data, filename):
        # Validate each transaction
        validated_data = []
        for tx in data:
            if isinstance(tx, Transaction):
                validated_data.append(tx.model_dump())
            else:
                # Assume dict, validate
                validated_tx = Transaction(**tx)
                validated_data.append(validated_tx.model_dump())
        
        with open(filename, 'w') as f:
            json.dump(validated_data, f, indent=4)
        print(f"[*] Successfully wrote {len(validated_data)} enhanced records to {filename}")