# uutils/parsers.py
import re
import json
import logging

logger = logging.getLogger("avangarde.parsers")

def extract_json(text: str) -> dict:
    """
    Robustly extracts and parses JSON from potentially messy LLM output.
    Handles markdown blocks, leading/trailing text, and malformed strings.
    """
    if not text:
        return {}

    # 1. Try to find JSON block inside markdown triple backticks
    match = re.search(r"
http://googleusercontent.com/immersive_entry_chip/0

### 🏁 Final State
* **`utils/parsers.py`**: Makes sure the LLM's "chatty" nature doesn't break your code.
* **`core/security.py`**: Gives you an audit trail in `logs/audit.log` so if you blow an account, you can actually see the reasoning the AI used.
* **`claw_robot.py`**: The clean orchestrator you asked for.

Everything is defined. No more "made up" placeholders. Go build your `logs/` directory and fire it up. 

Are we clear on the `extract_json` regex logic, or do you want me to tighten the `_emergency_regex_parse` for specific asset pairs?
