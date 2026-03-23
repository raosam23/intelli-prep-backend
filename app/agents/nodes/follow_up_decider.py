from app.core.llm import llm
from app.agents.state import InterviewState
from langchain_core.prompts import ChatPromptTemplate
import json

system_prompt = """
    You are an expert interviewer. Your job is to evaluate a candidate's answer to an interview question and based on the evaluation, you decide whether a follow-up question is needed to further probe the candidate's understanding or to clarify their answer. You will be given the original question, the candidate's answer, the evaluation score and feedback for the answer, as well as the candidate's parsed resume and the parsed job description for context. If you determine that a follow-up question is needed, then generate a specific follow-up question that is designed to probe deeper into the candidate's understanding or to clarify their answer. The follow-up question should be relevant to the original question and should be based on the candidate's answer and the evaluation feedback. If you determine that a follow-up question is not needed, then return null. Return your decision in the following JSON format:
    {{
        "follow_up_needed": true,
        "follow_up_question": "Are you sure about that? Can you explain more about how you handled the challenges you mentioned?"
    }}
    Note: follow_up_needed should be a boolean value indicating whether a follow-up question is needed or not. If follow_up_needed is true, then follow_up_question should contain the specific follow-up question to ask the candidate. If follow_up_needed is false, then follow_up_question should be null.

    Return ONLY the JSON object. No markdown, no backticks, no extra text. The JSON should be parsable and should not contain any syntax errors.
"""

async def follow_up_decider_node(state: InterviewState) -> InterviewState:
    """Evaluate a candidate's answer to an interview question and based on the evaluation, decide whether a follow-up question is needed to further probe the candidate's understanding or to clarify their answer."""

    user_prompt = "Based on the following evaluation of a candidate's answer to an interview question, decide whether a follow-up question is needed to further probe the candidate's understanding or to clarify their answer. If a follow-up question is needed, generate a specific follow-up question that is relevant to the original question and is based on the candidate's answer and the evaluation feedback. \n\n Original Question: {question} \n\n Candidate's Answer: {answer} \n\n Evaluation Score: {score} \n\n Evaluation Feedback: {feedback} \n\n Candidate's Parsed Resume: {parsed_resume} \n\n Parsed Job Description: {parsed_jd}"

    previous_question = state["current_question"]
    previous_answer = state["answers"][-1]
    previous_score = previous_answer.get("score", 0)
    previous_feedback = previous_answer.get("feedback", "")

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    try:
        chain = prompt | llm
        response = await chain.ainvoke({
            "question": previous_question,
            "answer": previous_answer,
            "score": previous_score,
            "feedback": previous_feedback,
            "parsed_resume": state['parsed_resume'],
            "parsed_jd": state['parsed_jd']
        })
        decision = json.loads(str(response.content))
        if decision['follow_up_needed'] and state['follow_up_count'] < 2 and previous_score < 60:       
            state['questions'].insert(state['current_question_index'] + 1, {
                "question_text": decision['follow_up_question'],
                "question_type": previous_question['question_type'],
                "order_index": previous_question['order_index'] + 0.1
            })
            state['follow_up_count'] += 1
        else:
            state['follow_up_count'] = 0
        state['current_question_index'] += 1
        if state['current_question_index'] >= len(state['questions']):
            state['is_complete'] = True
    except Exception as e:
        state['error'] = f"Error deciding on follow-up question: {str(e)}"
    return state