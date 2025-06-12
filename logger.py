# logger.py

import os
import json
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def log_prompt_and_response(prompt, response, tag="doc"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tag}_{timestamp}.json"
    with open(os.path.join(LOG_DIR, filename), "w", encoding="utf-8") as f:
        json.dump({"prompt": prompt, "response": response}, f, indent=2)
