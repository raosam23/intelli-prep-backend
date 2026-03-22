from app.agents.state import InterviewState
from app.core.llm import llm
from langchain_core.prompts import ChatPromptTemplate
import json

system_prompt = """
    You are a job description analyzer. You take in a raw job description and extract the relevant information from it to be used in the interview preparation process. You should extract the following information from the job description:
- Job Title: The title of the job position.
- Company Name: The name of the company offering the job.
- Required Skills: A list of skills that are required for the job.
- Preferred Skills: A list of skills that are preferred for the job, but not required.
- Experience Level: The level of experience required for the job (e.g. entry-level, mid-level, senior).
- Responsibilities: A list of the main responsibilities and duties associated with the job.
- Education Requirements: The educational qualifications required for the job.
- Interview Focus Areas: Specific areas that the interview should focus on based on the job description (e.g. technical skills, behavioral questions, problem-solving).
    You should return the extracted information in a structured format that can be easily used in the interview preparation process. The structured format should be a JSON object with the following structure:

{{
    "job_title": "Software Engineer",
    "company_name": "Tech Company",
    "required_skills": ["Python", "JavaScript", "SQL"],
    "preferred_skills": ["Django", "React"],
    "experience_level": "Mid-level",
    "responsibilities": [
        "Develop and maintain web applications",
        "Collaborate with cross-functional teams",
        "Participate in code reviews"
    ],
    "education_requirements": "Bachelor's degree in Computer Science or related field",
    "interview_focus_areas": ["Technical skills", "Behavioral questions", "Problem-solving"]
}}

    If any of the above information is not present in the resume, you should return null for that field.

    Return ONLY the JSON object as the response. Do not include any additional text or explanations or markdown formatting or backticks. The JSON should be parsable and should not contain any syntax errors.
"""

async def jd_analyzer_node(state: InterviewState) -> InterviewState:
    """Analyzes the job description and extracts relevant information to be used in the interview preparation process."""
    user_prompt = "Analyze the following job description and extract the relevant information: \n\n {jd_raw_text}"
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    try:
        chain = prompt | llm
        response = await chain.ainvoke({"jd_raw_text": state['jd_raw_text']})
        parsed_jd = json.loads(str(response.content))
        state['parsed_jd'] = parsed_jd
    except Exception as e:
        state['error'] = f"Error analyzing job description: {str(e)}"
    return state