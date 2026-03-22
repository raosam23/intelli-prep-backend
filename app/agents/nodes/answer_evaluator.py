from app.core.llm import llm
from app.agents.state import InterviewState
from langchain_core.prompts import ChatPromptTemplate
import json

system_prompt = """
    You are an expert interviewer. Your job is to evaluate a candidate's answer to an interview question and provide feedback on how well the answer addresses the question, as well as suggestions for improvement. You also should generate a score from 0 to 100 for the answers based on how well it addresses the question, the depth of the answer, and how well it demonstrates the candidate's skills and experience. You will be given the question, the candidate's answer, and the candidate's parsed resume and the parsed job description for context. Your evaluation should consider how well the answer addresses the question, the relevance and depth of the answer, and how well it demonstrates the candidate's skills and experience as they relate to the job description. Provide specific feedback on what was good about the answer and what could be improved, along with actionable suggestions for improvement. Return your evaluation in the following JSON format:
    {{
        "score": 80,
        "feedback": "The candidate provided a strong answer that directly addressed the question and demonstrated relevant skills and experience. They gave specific examples from their past work that showed how they have successfully handled similar situations. However, they could improve by providing more detail on the outcomes of their actions and how they measured success. Additionally, they could have mentioned any challenges they faced and how they overcame them to give a more complete picture of their experience."
    }}

    Return ONLY the JSON object. No markdown, no backticks, no extra text. The JSON should be parsable and should not contain any syntax errors.
"""

async def answer_evaluator_node(state: InterviewState) -> InterviewState:
    """Evaluates a candidate's answer to an interview question and provides feedback on how well the answer addresses the question, as well as suggestions for improvement."""
    user_prompt = "Evaluate the following answer to the interview question and provide a score from 0 to 100 along with feedback and suggestions for improvement. \n\n Question: {question} \n\n Candidate's Answer: {answer} \n\n Candidate's Parsed Resume: {parsed_resume} \n\n Parsed Job Description: {parsed_jd}"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])

    try:
        chain = prompt | llm
        response = await chain.ainvoke({
            "question": state["questions"][state["current_question_index"]],
            "answer": state["answers"][-1],
            "parsed_resume": state["parsed_resume"],
            "parsed_jd": state["parsed_jd"]
        })
        evaluation = json.loads(str(response.content))
        state['answers'][-1]['score'] = evaluation['score']
        state['answers'][-1]['feedback'] = evaluation['feedback']
    except Exception as e:
        state['error'] = f"Error evaluating answer: {str(e)}"
    return state