"""Request and agent output schemas reject malformed payloads."""

import uuid

import pytest
from pydantic import ValidationError

from app.agents.schemas.answer_evaluator_schema import AnswerEvaluatorOutput
from app.agents.schemas.final_evaluator_schema import FinalEvaluatorOutput
from app.agents.schemas.fit_scorer_schema import FitBreakdownScore, FitScorerOutput
from app.agents.schemas.follow_up_decider_schema import FollowUpDeciderOutput
from app.agents.schemas.question_generator_schema import Question, QuestionGeneratorOutput
from app.models.evaluation import Verdict
from app.models.interview_session import DifficultyLevel, InterviewType
from app.schemas.auth import RegisterRequest, TokenResponse, UpdateProfileRequest
from app.schemas.interview_session import CreateInterviewSessionRequest
from app.schemas.job_application import CreateJobApplicationRequest


def test_register_request_requires_a_valid_email_and_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(name="Ada", email="not-an-email", password="supersecret")
    with pytest.raises(ValidationError):
        RegisterRequest(name="Ada", email="ada@example.com", password="short")
    created = RegisterRequest(name="Ada", email="ada@example.com", password="supersecret")
    assert created.name == "Ada"


def test_update_profile_password_is_optional_but_length_checked() -> None:
    assert UpdateProfileRequest().password is None
    assert UpdateProfileRequest(name="Ada").name == "Ada"
    with pytest.raises(ValidationError):
        UpdateProfileRequest(password="short")


def test_token_response_defaults_to_bearer() -> None:
    token = TokenResponse(access_token="abc.def.ghi")
    assert token.token_type == "bearer"


def test_job_application_request_requires_a_resume_and_description() -> None:
    with pytest.raises(ValidationError):
        CreateJobApplicationRequest(resume_id=uuid.uuid4())
    created = CreateJobApplicationRequest(resume_id=uuid.uuid4(), jd_raw_text="Backend role")
    assert created.jd_raw_text == "Backend role"


def test_interview_session_request_bounds_questions_and_enums() -> None:
    payload = {
        "job_application_id": uuid.uuid4(),
        "num_questions": 0,
        "difficulty": "mid",
        "interview_type": "technical",
    }
    with pytest.raises(ValidationError):
        CreateInterviewSessionRequest(**payload)
    payload["num_questions"] = 2
    payload["difficulty"] = "wizard"
    with pytest.raises(ValidationError):
        CreateInterviewSessionRequest(**payload)
    created = CreateInterviewSessionRequest(
        job_application_id=payload["job_application_id"],
        num_questions=2,
        difficulty=DifficultyLevel.SENIOR,
        interview_type=InterviewType.BEHAVIORAL,
    )
    assert created.focus_area is None
    assert created.difficulty == DifficultyLevel.SENIOR


def test_fit_scorer_output_nests_the_breakdown() -> None:
    score = FitScorerOutput(
        fit_score=82,
        fit_breakdown_score=FitBreakdownScore(
            technical_skills_match=90,
            experience_match=70,
            education_match=80,
        ),
    )
    dumped = score.model_dump()
    assert dumped["fit_breakdown_score"]["technical_skills_match"] == 90


def test_question_generator_rejects_follow_up_as_a_planned_question_type() -> None:
    with pytest.raises(ValidationError):
        Question(question_text="Why?", question_type="followup", order_index=1)
    generated = QuestionGeneratorOutput(
        questions=[Question(question_text="Explain indexes", question_type=InterviewType.TECHNICAL, order_index=1)]
    )
    assert generated.questions[0].question_type == InterviewType.TECHNICAL


def test_answer_and_follow_up_outputs() -> None:
    answer = AnswerEvaluatorOutput(score=64, feedback="Add a concrete example.")
    assert answer.score == 64
    skipped = FollowUpDeciderOutput(follow_up_needed=False)
    assert skipped.follow_up_question is None
    asked = FollowUpDeciderOutput(follow_up_needed=True, follow_up_question="What was the impact?")
    assert asked.follow_up_question == "What was the impact?"


def test_final_evaluator_verdict_must_be_a_known_value() -> None:
    with pytest.raises(ValidationError):
        FinalEvaluatorOutput(
            communication_score=1,
            technical_score=1,
            problem_solving_score=1,
            overall_score=1,
            verdict="maybe",
        )
    evaluation = FinalEvaluatorOutput(
        communication_score=80,
        technical_score=90,
        problem_solving_score=70,
        overall_score=84,
        verdict="hire",
        improvement_tips=["Quantify the result"],
    )
    assert evaluation.verdict == Verdict.HIRE
    assert evaluation.improvement_tips == ["Quantify the result"]
