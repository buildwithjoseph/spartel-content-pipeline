import os
import requests
from openai import OpenAI

# Initialize the OpenAI-compatible client pointing to Groq's API
client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def fetch_github_trending_ai():
    print("Fetching live developer data from GitHub...")
    # Searching for recently created, highly-starred AI/LLM repositories
    url = "https://api.github.com/search/repositories?q=topic:artificial-intelligence+created:>2026-01-01&sort=stars&order=desc"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            items = response.json().get("items", [])[:5] # Take top 5 trending repos
            repo_data = []
            for item in items:
                repo_data.append(f"- Name: {item.get('name')}\n  Description: {item.get('description')}\n  Stars: {item.get('stargazers_count')}\n  URL: {item.get('html_url')}")
            return "\n".join(repo_data)
        else:
            print(f"GitHub API warning: Status {response.status_code}. Falling back to general analysis.")
            return "No live GitHub data retrieved."
    except Exception as e:
        print(f"Error fetching GitHub trends: {e}")
        return "No live GitHub data retrieved."

def generate_content_brief():
    print("Initializing AI Content Pipeline with Live Data...")
    
    # Fetch live data to ground the AI's output in reality
    live_data = fetch_github_trending_ai()
    
    system_prompt = (
        "You are an expert technical content architect focusing on AI engineering, "
        "GitHub trends, and data-driven infrastructure. Write with a pragmatic, "
        "anti-fluff, highly technical tone. Avoid marketing buzzwords."
    )
    
    user_prompt = (
        f"Analyze the following real-time trending open-source AI developer repositories pulled from GitHub:\n\n"
        f"{live_data}\n\n"
        "Based on these live data signals, generate a concise, data-backed technical brief highlighting "
        "an emerging pattern, high-demand architecture, or developer tooling shift. "
        "Include actionable code snippets or architectural insights where relevant."
    )

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content
        print("\n=== GENERATED DATA-DRIVEN BRIEF ===")
        print(content)
        print("===================================\n")

        filename = "generated_brief.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully saved data-driven output to {filename}")

    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    generate_content_brief()
