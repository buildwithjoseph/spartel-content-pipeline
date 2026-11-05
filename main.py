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
# PHASE 1: dev.to Public API (Demand Angles & Style Exemplar Extraction)
# -------------------------------------------------------------------
def fetch_devto_demand_and_exemplar():
    print("[Phase 1/5] Extracting dev.to demand angles and top article exemplar...")
    url = "https://dev.to/api/articles?tag=ai&top=7"
    headers = {"User-Agent": "Spartel-Content-Pipeline-Agent"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            articles = res.json()
            if not articles:
                return "No trending articles found.", "No exemplar text available."
            
            # Extract top 5 trends summary
            trends = []
            for art in articles[:5]:
                title = art.get("title", "")
                reactions = art.get("public_reactions_count", 0)
                tags = ", ".join(art.get("tag_list", []))
                trends.append(f"- Title: \"{title}\" ({reactions} reactions) | Tags: [{tags}]")
            trends_summary = "\n".join(trends)

            # Fetch full body markdown of the #1 ranked article to act as Style Exemplar
            top_article_id = articles[0].get("id")
            exemplar_res = requests.get(f"https://dev.to/api/articles/{top_article_id}", headers=headers, timeout=10)
            
            if exemplar_res.status_code == 200:
                exemplar_markdown = exemplar_res.json().get("body_markdown", "")[:3500]  # Cap snippet to fit context
            else:
                exemplar_markdown = "Failed to load full body of top article."

            return trends_summary, exemplar_markdown
        else:
            print(f"dev.to API warning: Status {res.status_code}")
            return "dev.to API skipped.", "No exemplar text available."
    except Exception as e:
        print(f"Error fetching dev.to data: {e}")
        return "Failed to fetch dev.to demand.", "No exemplar text available."

# -------------------------------------------------------------------
# PHASE 2: Technical Signal Extraction (GitHub + HN + Hugging Face)
# -------------------------------------------------------------------
def fetch_technical_signals():
    print("[Phase 2/5] Gathering technical evidence (GitHub, HN, HF)...")
    
    # 1. GitHub API Signals
    fourteen_days_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    token = os.environ.get("GH_TOKEN")
    gh_headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Spartel-Content-Pipeline-Agent"
    }
    if token:
        gh_headers["Authorization"] = f"token {token}"

    gh_query = f"topic:agentic-ai pushed:>{fourteen_days_ago}"
    gh_url = "https://api.github.com/search/repositories"
    gh_params = {"q": gh_query, "sort": "updated", "order": "desc", "per_page": 3}

    github_signals = []
    try:
        res = requests.get(gh_url, headers=gh_headers, params=gh_params, timeout=10)
        if res.status_code == 200:
            for item in res.json().get("items", []):
                name = item.get("full_name", "Unknown")
                stars = item.get("stargazers_count", 0)
                desc = item.get("description") or "No description."
                url = item.get("html_url", "")
                github_signals.append(f"- Repo: {name} ({stars} stars)\n  Desc: {desc}\n  URL: {url}")
    except Exception as e:
        print(f"GitHub fetch error: {e}")

    # 2. Hacker News & Hugging Face Context
    hn_signals, hf_signals = [], []
    try:
        hn_res = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=5)
        if hn_res.status_code == 200:
            for s_id in hn_res.json()[:15]:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{s_id}.json", timeout=3).json()
                if item and "title" in item and any(kw in item["title"].lower() for kw in ["ai", "llm", "agent", "python"]):
                    hn_signals.append(f"- HN: {item['title']} (Score: {item.get('score', 0)})")
                if len(hn_signals) >= 3:
                    break
    except:
        pass

    try:
        hf_res = requests.get("https://huggingface.co/api/daily_papers", timeout=5)
        if hf_res.status_code == 200:
            for item in hf_res.json()[:3]:
                p = item.get("paper", {})
                hf_signals.append(f"- Paper: {p.get('title', 'Untitled')}")
    except:
        pass

    gh_text = "\n".join(github_signals) if github_signals else "No fresh GitHub signals."
    hn_hf_text = "\n".join(hn_signals + hf_signals) if (hn_signals or hf_signals) else "No secondary context."

    return gh_text, hn_hf_text

# -------------------------------------------------------------------
# PHASE 3 & 4: Style Transfer Generation & Persona Filtering
# -------------------------------------------------------------------
def generate_humanized_article(devto_trends, github_data, hn_hf_data, exemplar_text):
    print("[Phase 3 & 4/5] Synthesizing thesis and applying Few-Shot Style Transfer...")

    system_prompt = (
        "You are an independent AI builder, tech explorer, and developer advocate publishing on dev.to. "
        "Your content is rooted in pragmatic AI engineering, local execution, agentic architectures, "
        "and nearshore infrastructure trade-offs (specifically bridging UK/EU engineering needs with "
        "high-caliber AI talent patterns). "
        "Your tone is sharp, pragmatic, anti-fluff, and directly grounded in backend engineering logic. "
        "Focus on system primitives, state management, latency, and real ROI trade-offs. "
        "STRICTLY FORBIDDEN: Corporate buzzwords ('robust', 'game-changer', 'seamless', 'landscape') and generic "
        "AI introductions ('In today's fast-paced tech world'). Always start directly with an engineering friction point."
    )

    user_prompt = f"""
    ### STYLE EXEMPLAR (REFERENCE MARKDOWN FROM TOP PERFORMING DEV.TO ARTICLE):
    Analyze the rhythm, sentence variance, paragraph length, and structural formatting of this exemplar:
    ---
    {exemplar_text}
    ---

    ### INPUT SIGNALS & EVIDENCE:
    1. **dev.to Demand Trends:**
    {devto_trends}

    2. **Rising GitHub Repositories:**
    {github_data}

    3. **Developer Community & Research Context:**
    {hn_hf_data}

    ### TASK:
    Write a complete, publication-ready article in Markdown for dev.to by connecting the demand trends with the GitHub code evidence.
    
    CRITICAL STYLE INSTRUCTIONS:
    - Mirror the structural cadence and human tone of the Style Exemplar provided above.
    - Write as an active AI builder sharing practical code primitives and architectural scar tissue.
    - Include:
      1. An arresting, non-clickbait technical title.
      2. An immediate hook focusing on a real developer pain point (e.g., latency, state, memory limits).
      3. A high-contrast Markdown Data Table correlating GitHub repos with market needs.
      4. An ASCII Architecture Flow Diagram illustrating component interactions.
      5. A clean, copy-pasteable 15–30 line Python snippet demonstrating a core primitive.
      6. A pragmatic trade-off analysis concluding with an open architectural question to trigger community comments.
    """

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Article generation failed: {e}")
        return None

# -------------------------------------------------------------------
# PHASE 5: Automated Staging to dev.to Drafts API
# -------------------------------------------------------------------
def push_devto_draft(title, content_markdown):
    print("\n[Phase 5/5] Pushing generated article to dev.to Drafts dashboard...")
    devto_key = os.environ.get("DEVTO_API_KEY")
    if not devto_key:
        print("⚠️ DEVTO_API_KEY secret not found. Skipping dev.to draft push.")
        return

    url = "https://dev.to/api/articles"
    headers = {
        "api-key": devto_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "article": {
            "title": title,
            "body_markdown": content_markdown,
            "published": False,  # Keeps it as a private draft for human review
            "tags": ["ai", "python", "architecture", "opensource"]
        }
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 201:
            draft_url = res.json().get("url", "")
            print(f"✅ Successfully created dev.to draft! Preview URL: {draft_url}")
        else:
            print(f"⚠️ dev.to Draft creation failed (Status {res.status_code}): {res.text}")
    except Exception as e:
        print(f"Error submitting draft to dev.to: {e}")

# -------------------------------------------------------------------
# MAIN PIPELINE EXECUTION FLOW
# -------------------------------------------------------------------
def main():
    devto_trends, exemplar_markdown = fetch_devto_demand_and_exemplar()
    github_data, hn_hf_data = fetch_technical_signals()

    article_md = generate_humanized_article(
        devto_trends=devto_trends,
        github_data=github_data,
        hn_hf_data=hn_hf_data,
        exemplar_text=exemplar_markdown
    )
    
    if article_md:
        # 1. Commit draft locally to repository
        with open("generated_brief.md", "w", encoding="utf-8") as f:
            f.write(article_md)
        print("\nSuccessfully saved draft locally to 'generated_brief.md'")

        # Extract title line for API submission
        lines = [line.strip() for line in article_md.split("\n") if line.strip()]
        article_title = lines[0].replace("#", "").strip() if lines else "Pragmatic AI Architecture Brief"

        # 2. Push to dev.to private drafts
        push_devto_draft(article_title, article_md)

if __name__ == "__main__":
    main()
