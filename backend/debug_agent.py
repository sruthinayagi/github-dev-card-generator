import asyncio
import os
import json
from google import adk
from google.genai import types
from agent import github_card_agent
from dotenv import load_dotenv

load_dotenv()

async def debug_agent():
    username = "sruthinayagi"
    session_id = f"debug_session_{username}_final"
    
    # Initialize services
    session_service = adk.sessions.InMemorySessionService()
    memory_service = adk.memory.InMemoryMemoryService()
    
    runner = adk.Runner(
        app_name="debug_runner",
        agent=github_card_agent,
        session_service=session_service,
        memory_service=memory_service,
        auto_create_session=True
    )
    
    print(f"--- Debugging Agent for: {username} ---")
    
    try:
        print("Running agent...")
        events = list(runner.run(
            user_id="debug_user",
            session_id=session_id,
            new_message=types.Content(
                parts=[types.Part(text=f"Generate a dev card for {username}")],
                role="user"
            )
        ))
        
        print(f"\nCaptured {len(events)} events.")
        
        for i, event in enumerate(events):
            author = event.author or "Agent"
            print(f"\n[Event {i}] Author: {author}")
            
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"  Text: {part.text.strip()[:200]}...")
                    if part.function_call:
                        print(f"  Function Call: {part.function_call.name}")
            
            # Check function responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_response:
                        print(f"  Function Response: {part.function_response.name}")

        # Check if file exists
        file_path = f"static/cards/{username}.html"
        if os.path.exists(file_path):
            print(f"\nSUCCESS: Card created at {file_path}")
            with open(file_path, 'r') as f:
                content = f.read()
                if "theme-" in content and 'class="badge"' in content:
                    print("Card content looks valid.")
                else:
                    print("Card content might be incomplete.")
        else:
            print(f"\nFAILURE: Card file not found at {file_path}")
            
    except Exception as e:
        print(f"\nEXCEPTION: {str(e)}")

if __name__ == "__main__":
    asyncio.run(debug_agent())
