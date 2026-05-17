import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google import adk
from google.genai import types
from agent import github_card_agent
from mcp_server import (
    scrape_github,
    analyze_profile,
    generate_card_html,
    save_card,
)

# Initialize FastAPI app
app = FastAPI(title="GitHub Dev Card Generator API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CARDS_DIR = os.path.join(STATIC_DIR, "cards")
os.makedirs(CARDS_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ADK Services and Runner
session_service = adk.sessions.InMemorySessionService()
memory_service = adk.memory.InMemoryMemoryService()
runner = adk.Runner(
    app_name="github_dev_card_generator",
    agent=github_card_agent,
    session_service=session_service,
    memory_service=memory_service,
    auto_create_session=True
)


async def generate_card_direct(username: str) -> dict:
    """Fallback generation path that does not depend on an LLM orchestration agent."""
    github_data = await scrape_github(username=username)
    if github_data.get("error"):
        raise HTTPException(status_code=404, detail=github_data["error"])

    analysis = await analyze_profile(github_data=github_data)
    html = generate_card_html(
        username=username,
        github_data=github_data,
        analysis=analysis,
    )
    card_url = save_card(username=username, html=html)

    return {
        "status": "success",
        "card_url": card_url,
        "html": html,
        "agent_summary": "Generated via direct fallback pipeline.",
    }

class GenerateRequest(BaseModel):
    username: str

@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}

@app.post("/generate")
async def generate_card(request: GenerateRequest):
    """Endpoint to trigger the agent to generate a dev card."""
    username = request.username.lower().strip()
    session_id = f"session_{username}"
    
    try:
        # Run the agent
        # The agent is instructed to call save_card which returns the path
        # Note: runner.run is a generator returning events.
        events = list(runner.run(
            user_id="default_user",
            session_id=session_id,
            new_message=types.Content(
                parts=[types.Part(text=f"Generate a dev card for {username}")],
                role="user"
            )
        ))
        
        # Extract the final summary from events
        agent_summary = ""
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        agent_summary += part.text
        
        # Look for the card URL in the response
        card_url = f"/static/cards/{username}.html"
        
        # Verify the file was actually created
        file_path = os.path.join(CARDS_DIR, f"{username}.html")
        if not os.path.exists(file_path):
            fallback_result = await generate_card_direct(username=username)
            fallback_result["status"] = "fallback_success"
            fallback_result["message"] = "Agent finished but card file was missing; used direct fallback pipeline."
            fallback_result["agent_response"] = agent_summary
            return fallback_result

        with open(file_path, "r") as f:
            html_content = f.read()

        return {
            "status": "success",
            "card_url": card_url,
            "html": html_content,
            "agent_summary": agent_summary
        }
    except Exception as e:
        fallback_result = await generate_card_direct(username=username)
        fallback_result["agent_summary"] += f" Agent path failed: {str(e)}"
        return fallback_result

@app.get("/card/{username}")
async def get_card(username: str):
    """Serve a specific generated card."""
    file_path = os.path.join(CARDS_DIR, f"{username}.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Card not found")
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    # Use port 8080 as requested for Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=8080)
