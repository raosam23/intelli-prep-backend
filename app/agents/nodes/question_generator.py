from app.core.llm import llm
from app.agents.state import InterviewState
from langchain_core.prompts import ChatPromptTemplate
import json

system_prompt = """
    You are an expert interviewer. Your job is to generate tailored interview questions for a candidate based on their resume, the job description, and their fit analysis.

    You will be given:
    - The candidate's parsed resume
    - The parsed job description
    - The fit breakdown score showing how well the candidate matches the job
    - The number of questions to generate
    - The difficulty level (junior, mid, senior)
    - The interview type (technical, behavioral, managerial, mixed)
    - An optional focus area

    Guidelines for generating questions:
    - Focus more questions on areas where the candidate has gaps (low fit scores)
    - Include questions that verify the candidate's stated strengths
    - Match the difficulty level — junior questions should be straightforward, senior questions should be deep and complex
    - Match the interview type — technical questions should test knowledge and problem solving, behavioral questions should follow the STAR format, managerial questions should test leadership and decision making
    - If a focus area is provided, prioritize questions around that area
    - Make questions specific to the candidate's background — reference their actual experience, skills and projects
    - Do not generate generic questions that could apply to any candidate

    Return a JSON array of questions with the following structure:
    [
        {{
            "question_text": "The actual interview question",
            "question_type": "technical",
            "order_index": 1
        }}
    ]

    Note: question_type must be exactly one of "technical", "behavioral", "managerial". The order_index increments after each question and indicates the order in which the questions should be asked in the interview. Also it should start from 1 for the first question.
    Return ONLY the JSON array. No markdown, no backticks, no extra text. The JSON should be parsable and should not contain any syntax errors.
"""

async def question_generator_node(state: InterviewState) -> InterviewState:
    """Generates tailored interview questions for a candidate based on their resume, the job description and their fit analysis."""
    user_prompt = "Generate {num_questions} {difficulty_level} {interview_type} interview questions for a candidate based on the following information: \n\n Parsed Resume: {parsed_resume} \n\n Parsed Job Description: {parsed_jd} \n\n Fit Breakdown Score: {fit_breakdown_score} \n\n Focus Area: {focus_area}"
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    try:
        chain = prompt | llm
        response = await chain.ainvoke({
            "num_questions": state['num_questions'],
            "difficulty_level": state['difficulty'],
            "interview_type": state['interview_type'],
            "parsed_resume": state['parsed_resume'],
            "parsed_jd": state['parsed_jd'],
            "fit_breakdown_score": state['fit_breakdown_score'],
            "focus_area": state['focus_area'] or "none"
        })
        state['questions'] = json.loads(str(response.content))
        state['current_question_index'] = 0
    except Exception as e:
        state['error'] = f"Error generating questions: {str(e)}"
    return state