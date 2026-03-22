from app.agents.state import InterviewState
from app.core.llm import llm
from langchain_core.prompts import ChatPromptTemplate
import json


system_prompt = """
    You are a resume parser. You take in a raw resume and extract the relevant information from it to be used in the interview preparation process. You should extract the following information from the resume:
- Contact Information: Name, email, phone number, LinkedIn profile, etc.
- Summary or Objective: A brief statement about the candidate's career goals and qualifications.
- Work Experience: For each job, extract the job title, company name, location, dates of employment, and a description of the responsibilities and achievements.
- Education: For each degree, extract the degree type, major, university name, location, and graduation date.
- Skills: A list of relevant skills, both technical and soft skills.
- Certifications: Any relevant certifications, including the name of the certification, the issuing organization, and the date obtained.
- Projects: For each project, extract the project name, a brief description, the technologies used, and the candidate's role in the project.

    You should return the extracted information in a structured format that can be easily used in the interview preparation process. The structured format should be a JSON object with the following structure:
{{
    "contact_information": {{
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "123-456-7890",
        "linkedin": "https://www.linkedin.com/in/johndoe"
    }},
    "summary": "A brief statement about the candidate's career goals and qualifications.",
    "work_experience": [
        {{
            "job_title": "Software Engineer",
            "company_name": "Tech Company",
            "location": "City, State",
            "dates_of_employment": "Jan 2020 - Present",
            "description": "Description of responsibilities and achievements."
        }}
    ],
    "education": [
        {{
            "degree_type": "Bachelor's",
            "major": "Computer Science",
            "university_name": "University Name",
            "location": "City, State",
            "graduation_date": "May 2020"
        }}
    ],
    "skills": ["Python", "JavaScript", "SQL"],
    "certifications": [
        {{
            "name": "Certification Name",
            "issuing_organization": "Organization Name",
            "date_obtained": "Jan 2021"
        }}
    ],
    "projects": [
        {{
            "project_name": "Project Name",
            "description": "Brief description of the project.",
            "technologies_used": ["Python", "Django"],
            "role": "Developer"
        }}
    ]
}}
    If any of the above information is not present in the resume, you should return null for that field.

    Return ONLY the JSON object as the response. Do not include any additional text or explanations or markdown formatting or backticks. The JSON should be parsable and should not contain any syntax errors.
"""

async def resume_parser_node(state: InterviewState) -> InterviewState:
    """
    Parses the resume from the state and updates the state with the parsed data.
    """
    raw_resume = state['raw_resume']
    user_prompt = "Please parse the following resume and extract the relevant information:\n\n This is the raw resume {raw_resume}"
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt)
    ])
    try:
        chain = prompt | llm
        response = await chain.ainvoke({"raw_resume": raw_resume})
        state['parsed_resume'] = json.loads(str(response.content))
    except Exception as e:
        state['error'] = f"Error parsing resume: {str(e)}"
    return state