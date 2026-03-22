from typing import TypedDict, Dict, List, Optional, Any

class InterviewState(TypedDict):
    # Session Info
    session_id: str
    user_id: str
    job_application_id: str

    # Resume Data
    raw_resume: str
    parsed_resume: Dict[str, Any]

    # Job Description Data
    jd_raw_text: str
    parsed_jd: Dict[str, Any]

    # Fit analysis
    fit_score: float
    fit_breakdown_score: Dict[str, Any]

    # Interview
    num_questions: int
    difficulty: str
    interview_type: str
    focus_area: Optional[str]
    questions: List[Dict[str, Any]]
    current_question_index: int
    answers: List[Dict[str, Any]]
    follow_up_count: int

    # Evaluation
    final_evaluation: Dict[str, Any]

    # Control Flow
    is_complete: bool
    error: Optional[str]