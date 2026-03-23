from app.core.llm import llm
from app.agents.state import InterviewState
from langchain_core.prompts import ChatPromptTemplate
import json

system_prompt = """
    You are are a fit scorer agent. Your job is to compare the parsed resume against the parsed job description and provide a fit score that indicates how well the candidate's resume matches the requirements of the job description. You should analyze the following aspects to determine the fit score:
    - Technical Skills Match: Compare the required and preferred skills from the job description with the skills listed in the resume. Consider both the number of matching skills and the relevance of those skills to the job. Understand how well the candidate's skills align with the job requirements.
    - Experience Match: Evaluate the candidate's work experience in relation to the required experience level and the responsibilities outlined in the job description. Consider the relevance of the candidate's past roles and achievements to the job they are applying for.
    - Education Match: Assess the candidate's educational background against the education requirements specidied int the job description. Consider the degree type, major and the reputation of the educational institution.
    - Overall Fit: Based on the above factors, provide an overall fit score that indicates how well the candidate's resume matches the job description. The fit score should be a number between 0 and 100, where 0 indicates no fit and 100 indicates a perfect fit.
    You should return the fit score and the fit breakdown in a structured format that can be easily used in the interview preparation process. The structured format should be a JSON object with the following structure:

    {{ 
    "fit_score": 85.5,
    "fit_breakdown_score": {{
        "technical_skills_match": 90,
        "experience_match": 80,
        "education_match": 85
        }}
    }}

    Return ONLY the JSON object as the response. Do not include any additional text or explanations or markdown formatting or backticks. The JSON should be parsable and should not contain any syntax errors.
    """

async def fit_scorer_node(state: InterviewState) -> InterviewState:
    """Compares the parsed resume against the parsed job description and provides a fit score that indicates how well the candidate's resume matches the requirements of the job description.
    """
    user_prompt = "Compare the following parsed resume against the parsed job description and provide a fit score: \n\n Resume: {parsed_resume} \n\n Job Description: {parsed_jd}"
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    try:
        chain = prompt | llm
        response = await chain.ainvoke({
            "parsed_resume": state['parsed_resume'],
            "parsed_jd": state['parsed_jd']
        })
        fit_data = json.loads(str(response.content))
        state['fit_score'] = fit_data['fit_score']
        state['fit_breakdown_score'] = fit_data['fit_breakdown_score']
    except Exception as e:
        state['error'] = f"Error calculating fit score: {str(e)}"
    return state