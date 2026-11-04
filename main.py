import os
import openai

# 1. Load the modular API key
api_key = os.environ.get("LLM_API_KEY")

if not api_key:
    raise ValueError("CRITICAL: LLM_API_KEY environment variable is missing or empty!")

# 2. Configure the OpenAI-compatible client for Groq
client = openai.OpenAI(
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1"
)

# 3. Define our anti-fluff technical system prompt and prompt payload
system_prompt = (
    "You are an expert AI engineering analyst. Write with a pragmatic, "
    "anti-fluff technical tone. Prioritize data-driven insights, architectural "
    "efficiency, and clear markdown structure. Avoid generic hype or filler."
)

user_prompt = (
    "Generate a concise technical briefing on current high-demand AI engineering "
    "skills based on recent developer trends and startup deployment patterns. "
    "Structure it with clear Markdown headings, actionable data points, and modular code patterns."
)

print("Connecting to Groq using openai/gpt-oss-120b...")

try:
    # 4. Call the model
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3, # Keeps output analytical and focused
        max_tokens=1500
    )

    content_output = response.choices[0].message.content
    print("\n=== GENERATED CONTENT BRIEF ===")
    print(content_output)
    print("===============================\n")

    # 5. Save the output to a markdown file so git can commit it back to your repo
    filename = "generated_brief.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content_output)
    print(f"Successfully saved output to {filename}")

except Exception as e:
    print(f"Pipeline execution failed: {e}")
    exit(1)
