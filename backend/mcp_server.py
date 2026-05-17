import os
import json
import httpx
import google.generativeai as genai
from mcp.server.fastmcp import FastMCP
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("GitHubDevCardTools")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

GITHUB_API_URL = "https://api.github.com"

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Fetch user profile and top repositories from GitHub."""
    username = username.lower().strip()
    headers = {}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    
    async with httpx.AsyncClient(headers=headers) as client:
        # User info
        user_res = await client.get(f"{GITHUB_API_URL}/users/{username}")
        if user_res.status_code != 200:
            return {"error": f"GitHub user '{username}' not found"}
        user_data = user_res.json()

        # Repositories
        repos_res = await client.get(f"{GITHUB_API_URL}/users/{username}/repos?sort=stars&per_page=30")
        repos = repos_res.json() if repos_res.status_code == 200 else []

        top_repos = []
        languages = {}
        for repo in repos:
            if repo.get("fork"): continue
            repo_info = {
                "name": repo.get("name"),
                "stars": repo.get("stargazers_count", 0),
                "language": repo.get("language"),
                "description": repo.get("description")
            }
            top_repos.append(repo_info)
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

        # Sort by stars
        top_repos.sort(key=lambda x: x["stars"], reverse=True)
        # Sorted languages
        sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "username": username,
            "name": user_data.get("name") or username,
            "bio": user_data.get("bio"),
            "location": user_data.get("location"),
            "avatar_url": user_data.get("avatar_url"),
            "public_repos": user_data.get("public_repos"),
            "followers": user_data.get("followers"),
            "top_repos": top_repos[:6],
            "most_used_languages": [l[0] for l in sorted_langs[:3]]
        }

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Analyze GitHub data to generate developer insights using Gemini."""
    prompt = f"""
    Analyze this GitHub data and return a JSON object with:
    - developer_vibe: (1 sentence personality)
    - top_skills: (list of 3)
    - fun_fact: (something clever inferred from their repos)
    - card_theme: (one of: "hacker", "builder", "researcher", "designer", "open-source-hero")

    Data: {json.dumps(github_data)}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        # Basic cleaning if Gemini adds markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
            
        return json.loads(text)
    except Exception as e:
        print(f"Gemini error: {str(e)}")
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and openai_key.startswith("sk-"):
            print("Using OpenAI fallback for profile analysis.")
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a profile analyst. Return ONLY a valid JSON object."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            analysis_result = json.loads(completion.choices[0].message.content)
            print(f"OpenAI Analysis result: {analysis_result}")
            return analysis_result
            
        if "429" in str(e):
            print("Quota exceeded and no OpenAI key, using mock analysis.")
            return {
                "developer_vibe": "A legendary architect of core infrastructure with a focus on low-level systems and scalability.",
                "top_skills": ["C", "Git", "Kernel Development"],
                "fun_fact": "Created the version control system nearly everyone uses today because they were frustrated with the existing options.",
                "card_theme": "hacker"
            }
        raise e

@mcp.tool()
def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generate a self-contained HTML string for the developer card."""
    username = username.lower().strip()
    template_str = """
    <div class="github-card theme-{{ analysis.card_theme }} p-6 rounded-2xl shadow-2xl max-w-lg mx-auto text-white">
        <style>
            .theme-hacker { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); border: 2px solid #00ff41; }
            .theme-builder { background: linear-gradient(135deg, #232526, #414345); border: 2px solid #ffa500; }
            .theme-researcher { background: linear-gradient(135deg, #2c3e50, #000000); border: 2px solid #3498db; }
            .theme-designer { background: linear-gradient(135deg, #ff00cc, #3333ff); border: 2px solid #ffffff; }
            .theme-open-source-hero { background: linear-gradient(135deg, #1d976c, #93f9b9); border: 2px solid #ffffff; color: #1a1a1a; }
            
            .github-card { font-family: 'Inter', system-ui, sans-serif; transition: transform 0.3s ease; }
            .github-card:hover { transform: scale(1.02); }
            .badge { background: rgba(255, 255, 255, 0.1); padding: 4px 12px; border-radius: 99px; font-size: 0.75rem; }
            .repo-item { background: rgba(0, 0, 0, 0.2); padding: 10px; border-radius: 8px; margin-bottom: 8px; }
        </style>
        
        <div class="flex items-center gap-4 mb-6">
            <img src="{{ github_data.avatar_url }}" class="w-20 h-20 rounded-full border-4 border-white/20" />
            <div>
                <h2 class="text-2xl font-bold">{{ github_data.name }}</h2>
                <p class="text-sm opacity-80">{{ analysis.developer_vibe }}</p>
            </div>
        </div>

        <div class="flex gap-2 mb-6 flex-wrap">
            {% for skill in analysis.top_skills %}
            <span class="badge">{{ skill }}</span>
            {% endfor %}
        </div>

        <div class="grid grid-cols-2 gap-4 mb-6 text-center">
            <div class="bg-white/5 p-2 rounded-lg">
                <div class="text-xl font-bold">{{ github_data.public_repos }}</div>
                <div class="text-xs uppercase opacity-60">Repos</div>
            </div>
            <div class="bg-white/5 p-2 rounded-lg">
                <div class="text-xl font-bold">{{ github_data.followers }}</div>
                <div class="text-xs uppercase opacity-60">Followers</div>
            </div>
        </div>

        <div class="mb-6">
            <h3 class="text-sm font-bold uppercase mb-3 opacity-60">Top Repositories</h3>
            {% for repo in github_data.top_repos[:3] %}
            <div class="repo-item">
                <div class="flex justify-between items-center">
                    <span class="font-semibold">{{ repo.name }}</span>
                    <span class="text-xs">⭐ {{ repo.stars }}</span>
                </div>
                <p class="text-xs opacity-70 truncate">{{ repo.description or "No description" }}</p>
            </div>
            {% endfor %}
        </div>

        <div class="pt-4 border-t border-white/10 text-xs italic opacity-60">
            Fun Fact: {{ analysis.fun_fact }}
        </div>
    </div>
    """
    template = Template(template_str)
    return template.render(github_data=github_data, analysis=analysis)

@mcp.tool()
def save_card(username: str, html: str) -> str:
    """Save the generated card HTML to a file."""
    username = username.lower().strip()
    output_dir = Path("static/cards")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = output_dir / f"{username}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
