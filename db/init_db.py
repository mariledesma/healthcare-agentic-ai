"""Initialize the database with the versioned additive migration."""
import json
from db.migrate import migrate

if __name__ == "__main__":
    print(json.dumps(migrate(), indent=2))
