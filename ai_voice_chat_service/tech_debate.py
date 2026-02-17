
import sys
import time
import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    # Try to find it in parent .env if not found
    parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gemini_poc", ".env")
    if os.path.exists(parent_env):
        from dotenv import dotenv_values
        config = dotenv_values(parent_env)
        GOOGLE_API_KEY = config.get("GEMINI_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)

class Agent:
    def __init__(self, name, prompt, model_name="gemini-2.0-flash"):
        self.name = name
        self.system_prompt = prompt
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt
        )

    def generate(self, input_text):
        try:
            response = self.model.generate_content(input_text)
            return response.text
        except Exception as e:
            return f"Error generating response: {e}"

# Define specialized prompts for this specific debate
BACKEND_ARCHITECT_PROMPT = """
You are a Senior Backend Architect. You prioritize system stability, latency, and scalability.
You are skeptical of "workarounds" if they introduce extra hops (latency) or security risks.
You prefer native SDKs because they usually offer better control over raw data.
However, you also know that Python version locking (sticking to old 3.10 for a library) is technical debt.
"""

FRONTEND_DEV_PROMPT = """
You are a Lead Frontend Developer. You love the "Browser-Relay" approach because it makes the client logic simple (just standard Web APIs).
You argue that aiming for "Universal Browser Support" is better than fighting with OS-specific SDKs (Windows vs Mac vs Linux).
You worry about the server load if we have to relay *everyone's* audio stream via WebSocket manually.
"""

PRODUCT_MANAGER_PROMPT = """
You are the Technical Product Manager. You care about "Time to Market" (MVP Speed) vs "Long-term Maintenance".
You want to know:
1. Will this workaround block us when we expand to Mobile Apps (iOS/Android)?
2. Is the latency acceptable for a "Real-time Voice Chat"?
3. Can we swap it out later easily?
"""

CRITICAL_REVIEWER_PROMPT = """
You are the Quality & Risk Lead. You look for the "gotchas".
You are concerned about:
- Latency double-hop (Browser -> Python Server -> Gemini -> Python Server -> Browser).
- Windows Audio Driver issues (which we just fought with).
- Future proofing: If Agora updates their API, does our relay break?
"""

def main():
    print("--- Architectural Debate: Browser-Relay vs. Native SDK ---")
    print("Context: We are building an AI Voice Chat on Windows. The Native Agora Python SDK does not support Python 3.13 (current env).")
    print("Choice A: Browser-Relay (Client sends audio -> Server -> Gemini). Universal, but extra hop.")
    print("Choice B: Native SDK (Downgrade to Python 3.10/3.11). Stable, but adds env complexity.")
    print("Goal: Decide the best path for MVP AND Long-term.")

    # Initialize Agents
    architect = Agent("Backend Architect", BACKEND_ARCHITECT_PROMPT)
    frontend = Agent("Frontend Dev", FRONTEND_DEV_PROMPT)
    manager = Agent("Product Manager", PRODUCT_MANAGER_PROMPT)
    reviewer = Agent("Critical Reviewer", CRITICAL_REVIEWER_PROMPT)

    agents = [manager, architect, frontend, reviewer]
    
    chat_history = "Initial Context: We need to chose between Browser-Relay (Python 3.13 friendly) vs Native SDK (Requires Py3.10). Plan for 5 rounds of debate.\n"

    for i in range(5):
        print(f"\n[Round {i+1}/5]")
        
        # Select speaker based on round
        if i == 0:
            speaker = manager # kickoff
        elif i == 1:
            speaker = architect # technical deep dive
        elif i == 2:
            speaker = frontend # counter perspective
        elif i == 3:
            speaker = reviewer # risk check
        else:
            speaker = manager # conclusion
            
        print(f"  -> {speaker.name} is speaking...")
        
        prompt = f"""
        Current Discussion Level: Round {i+1} of 5.
        
        Transcript so far:
        {chat_history[-4000:]}
        
        Please provide your argument, rebuttal, or synthesis based on your role.
        If this is the final round, the Product Manager must make a FINAL DECISION.
        """
        
        response = speaker.generate(prompt)
        print(f"     {speaker.name}: {response[:100]}...") # Print preview
        
        entry = f"\n**{speaker.name}**: {response}\n"
        chat_history += entry
        time.sleep(1)

    # Save the debate
    with open("tech_debate_result.md", "w", encoding="utf-8") as f:
        f.write("# Architectural Debate Result\n\n" + chat_history)

    print("\nDebate finished! Results saved to tech_debate_result.md")

if __name__ == "__main__":
    main()
