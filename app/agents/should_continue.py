from app.agents.state import InterviewState

def should_continue(state: InterviewState) -> str:
    """Determines whether the interview process should continue or if it is complete based on the current state of the interview."""
    if state['is_complete']:
        return "final_evaluator"
    return "interview_loop"