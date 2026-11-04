import os
import requests

api_key = os.environ.get("LLM_API_KEY")

print(f"DEBUG: LLM_API_KEY type is: {type(api_key)}")
print(f"DEBUG: LLM_API_KEY length is: {len(api_key) if api_key else 'None/Empty'}")

if not api_key:
    print("ERROR: LLM_API_KEY environment variable is missing or empty!")
    print("Check if your repository secret is named exactly 'LLM_API_KEY' in Settings > Secrets > Actions.")
    exit(1)
