import os
import requests

# Fixed to read LLM_API_KEY directly from the environment
api_key = os.environ.get("LLM_API_KEY")

if not api_key:
    print("ERROR: LLM_API_KEY environment variable is missing or empty!")
    exit(1)

url = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

print("Querying Groq API for active models...")

try:
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code == 200:
        models = response.json().get("data", [])
        print("\n===========================================")
        print("   ACTIVE GROQ MODELS FOR YOUR API KEY     ")
        print("===========================================")
        for m in models:
            print(f"- {m.get('id')}")
        print("===========================================\n")
    else:
        print(f"Failed with Status Code {response.status_code}: {response.text}")
except Exception as e:
    print(f"An error occurred: {e}")
