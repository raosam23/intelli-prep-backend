from app.core.llm import llm
from app.agents.state import InterviewState
from langchain_core.prompts import ChatPromptTemplate
import json

system_prompt = """
    You are an expert hiring manager. Your job is to evaluate a candidate's overall performance in an interview and provide a final hiring recommendation. You will be given the candidate's parsed resume, the parsed job description, and all the interview questions and answers along with their scores and feedback.

Based on this information, evaluate the candidate across the following dimensions:
- Communication Score (0-100): How clearly and effectively did the candidate communicate their thoughts and ideas throughout the interview?
- Technical Score (0-100): How well did the candidate demonstrate technical knowledge and skills relevant to the job?
- Problem Solving Score (0-100): How well did the candidate demonstrate problem solving ability and critical thinking?
- Overall Score (0-100): A weighted average of the above scores that reflects the candidate's overall performance in the interview.

Based on the scores, provide a hiring verdict:
- strong_hire: The candidate is an exceptional fit and should be hired immediately
- hire: The candidate is a good fit and should be hired
- no_decision: The candidate shows potential but needs further evaluation
- no_hire: The candidate is not a good fit for the role
- strong_no_hire: The candidate is clearly not a fit and should not be hired

Also provide a list of specific improvement tips for the candidate based on their performance in the interview. These should be actionable and specific to the candidate's weak areas.

Return your evaluation in the following JSON format:
{{
    "communication_score": 85,
    "technical_score": 90,
    "problem_solving_score": 80,
    "overall_score": 85,
    "verdict": "hire",
    "improvement_tips": [
        "Focus on providing more specific examples when answering behavioral questions",
        "Deepen your knowledge of system design concepts"
    ]
}}

Note: verdict must be exactly one of: strong_hire, hire, no_decision, no_hire, strong_no_hire

Return ONLY the JSON object. No markdown, no backticks, no extra text. The JSON should be parsable and should not contain any syntax errors.
"""

async def final_evaluator_node(state: InterviewState) -> InterviewState:
    """Evaluates a candidate's overall performance in an interview and provides a final hiring recommendation."""

    user_prompt = "Evaluate the candidate's overall performance in the interview and provide a final hiring recommendation based on the following information: \n\n Parsed Resume: {parsed_resume} \n\n Parsed Job Description: {parsed_jd} \n\n Interview Questions: {questions} \n\n Candidate's Answers: {answers}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    chain = prompt | llm

    try:
        response = await chain.ainvoke({
            "parsed_resume": state['parsed_resume'],
            "parsed_jd": state['parsed_jd'],
            "questions": state['questions'],
            "answers": state['answers']
        })
        state['final_evaluation'] = json.loads(str(response.content))
    except Exception as e:
        state['error'] = f"Error evaluating final performance: {str(e)}"
    return state