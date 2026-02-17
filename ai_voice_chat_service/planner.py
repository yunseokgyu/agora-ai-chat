
import sys
import os
import time

# Ensure playground is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Agent_Class.agents import Agent
# We can import default prompts but we might want to customize them or just inject context
from Agent_Class.prompts import (
    POSITIVE_PLANNER_PROMPT,
    CRITICAL_REVIEWER_PROMPT,
    BACKEND_ARCHITECT_PROMPT,
    ADMIN_SPECIALIST_PROMPT,
    UI_UX_DESIGNER_PROMPT,
    MONETIZATION_MANAGER_PROMPT
)

def main():
    print("Starting AI Voice Chat Service Planning - 20 Iterations Mode")
    
    # Project Context
    project_context = """
    Project: AI Voice Chat Service with Photorealistic Models
    Goal: Create a global service for voice chatting with AI characters (photorealistic).
    Key Tech: Agora API for real-time voice, LLMs for conversation, TTS for voice generation.
    Target Markets: South Korea, Japan, China, USA.
    Roadmap: 
    1. MVP: Companionship/Dating app.
    2. Expansion: Adult content.
    Platform: Mobile app (iOS/Android) and potentially Web.
    """

    # Initialize Agents
    # We prepend the project context to their system prompts so they always know what they are working on
    planner = Agent("Positive Planner", project_context + "\n" + POSITIVE_PLANNER_PROMPT)
    reviewer = Agent("Critical Reviewer", project_context + "\n" + CRITICAL_REVIEWER_PROMPT)
    backend = Agent("Backend Architect", project_context + "\n" + BACKEND_ARCHITECT_PROMPT)
    admin = Agent("Admin Specialist", project_context + "\n" + ADMIN_SPECIALIST_PROMPT)
    designer = Agent("UI/UX Designer", project_context + "\n" + UI_UX_DESIGNER_PROMPT)
    monetization = Agent("Monetization Manager", project_context + "\n" + MONETIZATION_MANAGER_PROMPT)

    agents = [planner, reviewer, backend, admin, designer, monetization]
    
    # Collaborative "Memory" - acts as the meeting minutes
    meeting_minutes = "Initial Project Idea: " + project_context + "\n"

    # Define Meeting Agenda for 20 Iterations
    agenda = [
        "1. Brainstorming Core Features & MVP Scope",
        "2. Technical Feasibility Check (Agora, TTS latency, Model selection)",
        "3. User Experience Flow (Onboarding to Chat)",
        "4. Critical Review of MVP Plan (Risks)",
        "5. Backend Architecture Design (Database, API)",
        "6. Frontend/Mobile Architecture",
        "7. Agora Integration Specifics",
        "8. AI Model Selection & Pipeline (LLM + TTS)",
        "9. Global Localization Strategy (KR, JP, CN, US)",
        "10. Cultural Nuances & Customization for each market",
        "11. Monetization Strategy (MVP)",
        "12. Payment Integration (Global Gateways)",
        "13. Adult Content Expansion Roadmap",
        "14. Safety, Moderation & Legal (Adult content specific)",
        "15. Admin Panel Requirements",
        "16. UI/UX Design Verification (Vibe Check)",
        "17. Performance Optimization Plan",
        "18. Marketing & Launch Strategy",
        "19. Final Review of All Components",
        "20. Consolidation & Final Plan Generation"
    ]

    for i, topic in enumerate(agenda):
        iteration = i + 1
        print(f"\n--- Meeting {iteration}: {topic} ---")
        
        # Determine who speaks in this meeting based on topic
        active_agents = []
        if "Brainstorming" in topic or "Roadmap" in topic:
            active_agents = [planner, designer, monetization]
        elif "Technical" in topic or "Architecture" in topic or "Agora" in topic or "AI Model" in topic or "Performance" in topic:
            active_agents = [backend, planner]
        elif "Review" in topic or "Safety" in topic:
            active_agents = [reviewer, admin]
        elif "User Experience" in topic or "Design" in topic:
            active_agents = [designer, planner]
        elif "Monetization" in topic or "Payment" in topic or "Marketing" in topic:
            active_agents = [monetization, planner]
        elif "Global" in topic or "Cultural" in topic:
            active_agents = [planner, monetization, designer]
        elif "Admin" in topic:
            active_agents = [admin, backend]
        else:
            active_agents = agents # All hands on deck for final validaton

        # Run the meeting
        meeting_output = f"\n## Meeting {iteration}: {topic}\n"
        
        # Context for this meeting is the accumulator
        # We limit context length to avoid token limits if necessary, but 2.0 Flash has large window.
        # For efficiency, we pass the LAST 3 meetings summary + The full topic
        
        current_discussion = ""
        
        for agent in active_agents:
            print(f"  -> {agent.name} is speaking...")
            # Prompt the agent to contribute to the topic based on previous minutes
            prompt = f"""
            Agenda Topic: {topic}
            
            Current Meeting Minutes so far:
            {meeting_minutes[-8000:] if len(meeting_minutes) > 8000 else meeting_minutes}
            
            Please provide your input, designs, or critique regarding this topic.
            Be specific and detailed.
            """
            
            contribution = agent.generate(prompt)
            current_discussion += f"### {agent.name}\n{contribution}\n\n"
            print(f"     (Contributed {len(contribution)} chars)")
        
        meeting_minutes += meeting_output + current_discussion
        time.sleep(1) # Be nice to the API

    # Save Final Report
    output_path = os.path.join(os.path.dirname(__file__), "project_plan.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# AI Voice Chat Service - Comprehensive Project Plan\nGenerated via 20-Iteration Agent Vibe Coding\n\n{meeting_minutes}")

    print(f"\nPlanning complete! Plan saved to {output_path}")

if __name__ == "__main__":
    main()
