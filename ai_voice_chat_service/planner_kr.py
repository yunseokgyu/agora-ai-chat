
import sys
import os
import time

# Ensure playground is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Agent_Class.agents import Agent
from Agent_Class.prompts import (
    POSITIVE_PLANNER_PROMPT,
    CRITICAL_REVIEWER_PROMPT,
    BACKEND_ARCHITECT_PROMPT,
    ADMIN_SPECIALIST_PROMPT,
    UI_UX_DESIGNER_PROMPT,
    MONETIZATION_MANAGER_PROMPT
)

def main():
    print("AI 음성 채팅 서비스 기획 시작 - 20단계 반복 (한국어 모드)")
    
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

    IMPORTANT: ALL DISCUSSIONS AND OUTPUTS MUST BE IN KOREAN (한국어).
    """

    # Initialize Agents with Korean context injection
    # We prepend the project context to their system prompts so they always know what they are working on
    planner = Agent("Positive Planner", project_context + "\n" + POSITIVE_PLANNER_PROMPT)
    reviewer = Agent("Critical Reviewer", project_context + "\n" + CRITICAL_REVIEWER_PROMPT)
    backend = Agent("Backend Architect", project_context + "\n" + BACKEND_ARCHITECT_PROMPT)
    admin = Agent("Admin Specialist", project_context + "\n" + ADMIN_SPECIALIST_PROMPT)
    designer = Agent("UI/UX Designer", project_context + "\n" + UI_UX_DESIGNER_PROMPT)
    monetization = Agent("Monetization Manager", project_context + "\n" + MONETIZATION_MANAGER_PROMPT)

    agents = [planner, reviewer, backend, admin, designer, monetization]
    
    # Collaborative "Memory"
    meeting_minutes = "Initial Project Idea: " + project_context + "\n"

    # Define Meeting Agenda for 20 Iterations (Titles in Korean for clarity in logs)
    agenda = [
        "1. Brainstorming Core Features & MVP Scope (핵심 기능 및 MVP 범위 브레인스토밍)",
        "2. Technical Feasibility Check (기술적 타당성 검토 - Agora, TTS, Model)",
        "3. User Experience Flow (사용자 경험 흐름 - 온보딩부터 채팅까지)",
        "4. Critical Review of MVP Plan (MVP 기획에 대한 비판적 검토 및 리스크 분석)",
        "5. Backend Architecture Design (백엔드 아키텍처 설계 - DB, API)",
        "6. Frontend/Mobile Architecture (프론트엔드/모바일 아키텍처)",
        "7. Agora Integration Specifics (아고라 연동 상세)",
        "8. AI Model Selection & Pipeline (AI 모델 선정 및 파이프라인 - LLM + TTS)",
        "9. Global Localization Strategy (글로벌 현지화 전략 - 한/중/일/미)",
        "10. Cultural Nuances & Customization (시장별 문화적 특성 및 최적화)",
        "11. Monetization Strategy (수익화 전략 - MVP)",
        "12. Payment Integration (글로벌 결제 연동)",
        "13. Adult Content Expansion Roadmap (성인물 확장 로드맵)",
        "14. Safety, Moderation & Legal (안전, 중재 및 법적 이슈)",
        "15. Admin Panel Requirements (관리자 패널 요구사항)",
        "16. UI/UX Design Verification (UI/UX 디자인 점검 - 바이브 체크)",
        "17. Performance Optimization Plan (성능 최적화 계획)",
        "18. Marketing & Launch Strategy (마케팅 및 런칭 전략)",
        "19. Final Review of All Components (전체 구성 요소 최종 검토)",
        "20. Consolidation & Final Plan Generation (종합 및 최종 기획서 생성)"
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
        
        current_discussion = ""
        
        for agent in active_agents:
            print(f"  -> {agent.name} is speaking... (Korean Mode)")
            # Prompt the agent to contribute to the topic based on previous minutes
            prompt = f"""
            Agenda Topic: {topic}
            
            Current Meeting Minutes so far:
            {meeting_minutes[-8000:] if len(meeting_minutes) > 8000 else meeting_minutes}
            
            Please provide your input, designs, or critique regarding this topic.
            **IMPORTANT: WRITE EVERYTHING IN KOREAN (한국어).**
            Be specific and detailed.
            """
            
            contribution = agent.generate(prompt)
            current_discussion += f"### {agent.name}\n{contribution}\n\n"
            print(f"     (Contributed {len(contribution)} chars)")
        
        meeting_minutes += meeting_output + current_discussion
        time.sleep(1) # Be nice to the API

    # Save Final Report
    output_path = os.path.join(os.path.dirname(__file__), "project_plan_kr.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# AI 음성 채팅 서비스 - 종합 기획서 (한국어)\n20단계 에이전트 바이브 코딩 생성본\n\n{meeting_minutes}")

    print(f"\nPlanning complete! Plan saved to {output_path}")

if __name__ == "__main__":
    main()
