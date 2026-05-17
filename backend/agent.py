import os
from google import adk
from google.adk.tools import McpToolset
from mcp import StdioServerParameters
from dotenv import load_dotenv

load_dotenv()

# Common instructions for both agents
AGENT_INSTRUCTION = (
    "You are a GitHub profile analyst and dev card generator. "
    "Strictly follow this sequence for every username given:\n"
    "1. Call `scrape_github(username='<given_username>')`.\n"
    "2. Call `analyze_profile(github_data=<result_from_step_1>)`.\n"
    "3. Call `generate_card_html(username='<given_username>', github_data=<result_from_step_1>, analysis=<result_from_step_2>)`.\n"
    "4. Call `save_card(username='<given_username>', html=<result_from_step_3>)`.\n"
    "Use the exact username provided by the user (lowercase it if needed). "
    "Never skip steps. If you encounter an error (like user not found), tell the user and stop. "
    "Be enthusiastic and creative with the vibe and fun fact!"
)

# Common MCP tools configuration
mcp_toolset = McpToolset(
    connection_params=StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server.py"],
        env={**os.environ, "PYTHONPATH": os.path.dirname(__file__)}
    )
)

# Gemini Agent (Primary)
gemini_card_agent = adk.Agent(
    name="gemini_card_agent",
    instruction=AGENT_INSTRUCTION,
    model="gemini-2.0-flash",
    tools=[mcp_toolset]
)

# OpenAI Agent
openai_key = os.getenv("OPENAI_API_KEY")
openai_card_agent = None
if openai_key and openai_key.startswith("sk-"):
    from google.adk.models import LiteLlm
    openai_card_agent = adk.Agent(
        name="openai_card_agent",
        instruction=AGENT_INSTRUCTION,
        model=LiteLlm(model="openai/gpt-4o", api_key=openai_key),
        tools=[mcp_toolset]
    )

# Prefer OpenAI when available to avoid Gemini free-tier quota failures.
github_card_agent = openai_card_agent or gemini_card_agent
