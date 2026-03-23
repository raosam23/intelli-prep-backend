from app.agents.state import InterviewState

async def interview_loop_node(state: InterviewState) -> InterviewState:
    """Main loop of the interview process. This node will be called repeatedly until the interview is complete. It will determine the next question to ask the candidate, evaluate the candidate's answer to the previous question, and decide whether a follow-up question is needed based on the evaluation."""

    current_question = state['questions'][state['current_question_index']]
    state['current_question'] = current_question
    return state
