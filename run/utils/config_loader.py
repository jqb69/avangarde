# utils/config_loader.py
import yaml
from pathlib import Path

def load_config():
    # Gets the path to avangarde/run/utils, then goes up two levels to /avangarde/config.yaml
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_path = base_dir / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"❌ FATAL: config.yaml missing at {config_path}")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# Load it once when the app starts
APP_CONFIG = load_config()
