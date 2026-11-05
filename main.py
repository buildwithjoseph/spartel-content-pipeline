import os
import requests
from datetime import datetime, timedelta
from openai import OpenAI

# Initialize Groq client via OpenAI-compatible endpoint
client = OpenAI(
    api_key=os.environ.get("LLM_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# -------------------------------------------------------------------
# SOURCE 1: GitHub API (Active Repositories & Tooling Shifts)
# -------------------------------------------------------------------
def fetch_github_signals():
    print("[1/3] Fetching live GitHub signals...")
    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    
    token = os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    query = f"topic:ai OR topic:llm pushed:>{fourteen_days_ago} stars:>50"
    url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc"

    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            items = res.json().get("items", [])[:5]
            signals = []
            for item in items:
                name = item.get("name", "Unknown Repo")
                stars = item.get("stargazers_count", 0)
                desc = item.get("description") or "No description provided."
                html_url = item.get("html_url", "")
                signals.append(f"- Repo: {name} ({stars} stars)\n  Description: {desc}\n  URL: {html_url}")
            return "\n".join(signals) if signals else "No recent GitHub matches found."
        else:
            print(f"GitHub API Error Status: {res.status_code}")
            return "GitHub API request throttled or failed."
    except Exception as e:
        print(f"Error fetching GitHub data: {e}")
        return "Failed to fetch GitHub data."

# -------------------------------------------------------------------
# SOURCE 2: Hacker News Official Firebase API (Developer Discussions)
# -------------------------------------------------------------------
def fetch_hackernews_signals():
    print("[2/3] Fetching live Hacker News developer discussions...")
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    
    try:
        res = requests.get(top_stories_url, timeout=10)
        if res.status_code == 200:
            story_ids = res.json()[:30]
            ai_stories = []
            keywords = ["ai", "llm", "agent", "gpu", "python", "model", "open source", "rust"]
            
            for s_id in story_ids:
                item_url = f"https://hacker-news.firebaseio.com/v0/item/{s_id}.json"
                story_res = requests.get(item_url, timeout=5)
                if story_res.status_code == 200:
                    story = story_res.json() or {}
                    title = story.get("title", "")
                    if title and any(kw in title.lower() for kw in keywords):
                        score = story.get("score", 0)
                        link = story.get("url") or f"https://news.ycombinator.com/item?id={s_id}"
                        ai_stories.append(f"- Title: {title} (Score: {score}) | Link: {link}")
                    if len(ai_stories) >= 5:
                        break
            return "\n".join(ai_stories) if ai_stories else "No AI-specific discussions found in top stories."
        return "Failed to fetch Hacker News top stories."
    except Exception as e:
        print(f"Error fetching Hacker News data: {e}")
        return "Failed to fetch Hacker News data."

# -------------------------------------------------------------------
# SOURCE 3: Hugging Face Daily Papers API (Research Papers)
# -------------------------------------------------------------------
def fetch_huggingface_papers():
    print("[3/3] Fetching latest Hugging Face daily AI papers...")
    url = "https://huggingface.co/api/daily_papers"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            papers = res.json()[:5]
            paper_signals = []
            for item in papers:
                p = item.get("paper", {}) if isinstance(item, dict) else {}
                title = p.get("title", "Untitled Paper")
                summary = p.get("summary") or "No summary available."
                summary_snippet = summary.replace("\n", " ")[:150]
                paper_signals.append(f"- Paper: {title}\n  Summary snippet: {summary_snippet}...")
            return "\n".join(paper_signals) if paper_signals else "No daily papers fetched."
        return "Failed to fetch Hugging Face paper API."
    except Exception as e:
        print(f"Error fetching Hugging Face papers: {e}")
        return "Failed to fetch paper signals."

# -------------------------------------------------------------------
# MAIN PIPELINE SYNTHESIS
# -------------------------------------------------------------------
def generate_content_brief():
    print("\n--- AGGREGATING LIVE DATA SOURCES ---")
    github_data = fetch_github_signals()
    hn_data = fetch_hackernews_signals()
    hf_data = fetch_huggingface_papers()

    aggregated_context = (
        f"### LIVE GITHUB REPOSITORIES (LAST 14 DAYS):\n{github_data}\n\n"
        f"### HACKER NEWS DEVELOPER DISCUSSIONS:\n{hn_data}\n\n"
        f"### HUGGING FACE DAILY RESEARCH PAPERS:\n{hf_data}"
    )

    print("\n--- SYNTHESIZING BRIEF WITH OPENAI/GPT-OSS-120B ---")

    system_prompt = (
        "You are an expert technical content architect focusing on AI engineering, "
        "GitHub trends, and data-driven infrastructure. Write with a pragmatic, "
        "anti-fluff, highly technical tone. Avoid marketing buzzwords."
    )

    user_prompt = f"""
    Analyze the following real-time developer and research signals fetched directly from GitHub, Hacker News, and Hugging Face:

    {aggregated_context}

    Based strictly on these live multi-source signals:
    1. Provide a 'Data Signal Table' summarizing key takeaways across code repos, community sentiment, and research.
    2. Identify the single biggest 'Emerging Architectural Pattern' taking shape right now.
    3. Include a concise ASCII architecture diagram illustrating the interaction between these components.
    4. Provide an actionable, production-ready Python or Rust code snippet demonstrating a core primitive from these trends.
    """

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        content = response.choices[0].message.content

        filename = "generated_brief.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nSuccessfully generated and saved multi-source brief to '{filename}'!")

    except Exception as e:
        print(f"Pipeline synthesis failed: {e}")
        exit(1)

if __name__ == "__main__":
    generate_content_brief()
