"""LangGraph node behavior with the LLM chain mocked out.

Each node builds `prompt | llm` (or a structured-output runnable). The prompt
template is replaced so the pipe returns a chain whose `ainvoke` is an AsyncMock.
No OpenAI request is made.
"""

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes.answer_evaluator import answer_evaluator_node
from app.agents.nodes.final_evaluator import final_evaluator_node
from app.agents.nodes.fit_scorer import fit_scorer_node
from app.agents.nodes.follow_up_decider import follow_up_decider_node
from app.agents.nodes.interview_loop import interview_loop_node
from app.agents.nodes.jd_analyzer import jd_analyzer_node
from app.agents.nodes.question_generator import question_generator_node
from app.agents.nodes.resume_parser import resume_parser_node
from app.agents.schemas.answer_evaluator_schema import AnswerEvaluatorOutput
from app.agents.schemas.final_evaluator_schema import FinalEvaluatorOutput
from app.agents.schemas.fit_scorer_schema import FitBreakdownScore, FitScorerOutput
from app.agents.schemas.follow_up_decider_schema import FollowUpDeciderOutput
from app.agents.schemas.question_generator_schema import Question as GeneratedQuestion
from app.agents.schemas.question_generator_schema import QuestionGeneratorOutput
from app.models.evaluation import Verdict
from app.models.interview_session import InterviewType
from app.models.question import QuestionType
from tests.factories import interview_state


@contextmanager
def fake_chain(module: str, result=None, error: Exception | None = None):
    chain = MagicMock()
    if error is not None:
        chain.ainvoke = AsyncMock(side_effect=error)
    else:
        chain.ainvoke = AsyncMock(return_value=result)
    prompt = MagicMock()
    prompt.__or__.return_value = chain
    with patch(f"{module}.ChatPromptTemplate.from_messages", return_value=prompt):
        yield chain


def _json_message(payload: dict) -> MagicMock:
    message = MagicMock()
    message.content = json.dumps(payload)
    return message


@pytest.mark.asyncio
async def test_resume_parser_stores_json_from_the_model() -> None:
    payload = {"skills": ["Python"], "summary": "Backend engineer"}
    state = interview_state()
    with fake_chain("app.agents.nodes.resume_parser", result=_json_message(payload)) as chain:
        updated = await resume_parser_node(state)

    assert updated["parsed_resume"] == payload
    assert chain.ainvoke.await_args.args[0]["raw_resume"] == state["raw_resume"]


@pytest.mark.asyncio
async def test_resume_parser_keeps_prior_data_when_the_model_fails() -> None:
    state = interview_state(parsed_resume={"keep": True})
    message = MagicMock()
    message.content = "{not json"
    with fake_chain("app.agents.nodes.resume_parser", result=message):
        updated = await resume_parser_node(state)
    assert updated["parsed_resume"] == {"keep": True}
    assert updated["error"].startswith("Error parsing resume:")

    with fake_chain("app.agents.nodes.resume_parser", error=RuntimeError("timeout")):
        updated = await resume_parser_node(interview_state())
    assert "timeout" in updated["error"]


@pytest.mark.asyncio
async def test_jd_analyzer_stores_the_parsed_description() -> None:
    payload = {"job_title": "Backend Engineer", "required_skills": ["Python"]}
    state = interview_state()
    with fake_chain("app.agents.nodes.jd_analyzer", result=_json_message(payload)) as chain:
        updated = await jd_analyzer_node(state)

    assert updated["parsed_jd"] == payload
    assert chain.ainvoke.await_args.args[0]["jd_raw_text"] == state["jd_raw_text"]


@pytest.mark.asyncio
async def test_jd_analyzer_records_model_errors() -> None:
    state = interview_state(parsed_jd={"keep": True})
    with fake_chain("app.agents.nodes.jd_analyzer", error=RuntimeError("unavailable")):
        updated = await jd_analyzer_node(state)
    assert updated["parsed_jd"] == {"keep": True}
    assert updated["error"].startswith("Error analyzing job description:")


@pytest.mark.asyncio
async def test_fit_scorer_writes_the_score_and_breakdown() -> None:
    output = FitScorerOutput(
        fit_score=77.5,
        fit_breakdown_score=FitBreakdownScore(
            technical_skills_match=80,
            experience_match=70,
            education_match=75,
        ),
    )
    state = interview_state()
    with fake_chain("app.agents.nodes.fit_scorer", result=output) as chain:
        updated = await fit_scorer_node(state)

    assert updated["fit_score"] == 77.5
    assert updated["fit_breakdown_score"] == {
        "technical_skills_match": 80,
        "experience_match": 70,
        "education_match": 75,
    }
    sent = chain.ainvoke.await_args.args[0]
    assert sent["parsed_resume"] == state["parsed_resume"]
    assert sent["parsed_jd"] == state["parsed_jd"]


@pytest.mark.asyncio
async def test_fit_scorer_records_model_errors() -> None:
    state = interview_state(fit_score=12.0)
    with fake_chain("app.agents.nodes.fit_scorer", error=RuntimeError("schema mismatch")):
        updated = await fit_scorer_node(state)
    assert updated["fit_score"] == 12.0
    assert updated["error"].startswith("Error calculating fit score:")


@pytest.mark.asyncio
async def test_question_generator_resets_the_index_and_passes_focus() -> None:
    output = QuestionGeneratorOutput(
        questions=[
            GeneratedQuestion(
                question_text="Explain indexes",
                question_type=InterviewType.TECHNICAL,
                order_index=1,
            ),
            GeneratedQuestion(
                question_text="Tell me about a conflict",
                question_type=InterviewType.BEHAVIORAL,
                order_index=2,
            ),
        ]
    )
    state = interview_state(current_question_index=4, focus_area=None)
    with fake_chain("app.agents.nodes.question_generator", result=output) as chain:
        updated = await question_generator_node(state)

    assert updated["current_question_index"] == 0
    assert [question["question_text"] for question in updated["questions"]] == [
        "Explain indexes",
        "Tell me about a conflict",
    ]
    assert chain.ainvoke.await_args.args[0]["focus_area"] == "none"
    assert chain.ainvoke.await_args.args[0]["num_questions"] == state["num_questions"]

    focused = interview_state(focus_area="postgres")
    with fake_chain("app.agents.nodes.question_generator", result=output) as chain:
        await question_generator_node(focused)
    assert chain.ainvoke.await_args.args[0]["focus_area"] == "postgres"


@pytest.mark.asyncio
async def test_question_generator_does_not_advance_when_the_model_fails() -> None:
    state = interview_state(current_question_index=3, questions=[])
    with fake_chain("app.agents.nodes.question_generator", error=RuntimeError("empty completion")):
        updated = await question_generator_node(state)
    assert updated["current_question_index"] == 3
    assert updated["questions"] == []
    assert updated["error"].startswith("Error generating questions:")


@pytest.mark.asyncio
async def test_interview_loop_selects_the_question_at_the_current_index() -> None:
    state = interview_state()
    updated = await interview_loop_node(state)
    assert updated["current_question"] == state["questions"][0]

    state["current_question_index"] = 1
    updated = await interview_loop_node(state)
    assert updated["current_question"]["question_text"] == "How do you test a FastAPI service?"


@pytest.mark.asyncio
async def test_answer_evaluator_scores_only_the_latest_answer() -> None:
    output = AnswerEvaluatorOutput(score=82, feedback="Cite a metric.")
    state = interview_state(
        answers=[
            {"answer_text": "first", "score": None, "feedback": None},
            {"answer_text": "second", "score": None, "feedback": None},
        ]
    )
    with fake_chain("app.agents.nodes.answer_evaluator", result=output) as chain:
        updated = await answer_evaluator_node(state)

    assert updated["answers"][0]["score"] is None
    assert updated["answers"][1]["score"] == 82
    assert updated["answers"][1]["feedback"] == "Cite a metric."
    assert chain.ainvoke.await_args.args[0]["answer"]["answer_text"] == "second"


@pytest.mark.asyncio
async def test_answer_evaluator_records_errors_including_a_missing_answer() -> None:
    empty = interview_state(answers=[])
    with fake_chain("app.agents.nodes.answer_evaluator", result=AnswerEvaluatorOutput(score=1, feedback="x")):
        updated = await answer_evaluator_node(empty)
    assert updated["error"].startswith("Error evaluating answer:")

    state = interview_state(answers=[{"answer_text": "x", "score": None, "feedback": None}])
    with fake_chain("app.agents.nodes.answer_evaluator", error=RuntimeError("boom")):
        updated = await answer_evaluator_node(state)
    assert "boom" in updated["error"]
    assert updated["answers"][0]["score"] is None


@pytest.mark.parametrize(
    ("needed", "count", "score", "inserted", "expected_count"),
    [
        (True, 0, 50, True, 1),
        (True, 1, 59, True, 2),
        (True, 2, 10, False, 0),
        (True, 0, 60, False, 0),
        (False, 1, 10, False, 0),
    ],
)
@pytest.mark.asyncio
async def test_follow_up_rules(needed: bool, count: int, score: float, inserted: bool, expected_count: int) -> None:
    questions = [
        {"question_text": "Q1", "question_type": "technical", "order_index": 1},
        {"question_text": "Q2", "question_type": "technical", "order_index": 2},
    ]
    state = interview_state(
        questions=list(questions),
        current_question=dict(questions[0]),
        current_question_index=0,
        follow_up_count=count,
        answers=[{"answer_text": "because", "score": score, "feedback": "thin"}],
    )
    output = FollowUpDeciderOutput(
        follow_up_needed=needed,
        follow_up_question="Can you go deeper?" if needed else None,
    )
    with fake_chain("app.agents.nodes.follow_up_decider", result=output):
        updated = await follow_up_decider_node(state)

    assert updated["current_question_index"] == 1
    assert updated["is_complete"] is False
    assert updated["follow_up_count"] == expected_count
    if inserted:
        follow_up = updated["questions"][1]
        assert follow_up["question_text"] == "Can you go deeper?"
        assert follow_up["question_type"] == QuestionType.FOLLOWUP
        assert follow_up["order_index"] == round(1 + ((count + 1) / 10), 1)
        assert len(updated["questions"]) == 3
    else:
        assert len(updated["questions"]) == 2


@pytest.mark.asyncio
async def test_follow_up_on_the_last_question_keeps_the_interview_open() -> None:
    question = {"question_text": "Only question", "question_type": "technical", "order_index": 4}
    state = interview_state(
        questions=[question],
        current_question=dict(question),
        current_question_index=0,
        follow_up_count=0,
        answers=[{"answer_text": "unsure", "score": 20, "feedback": "vague"}],
    )
    output = FollowUpDeciderOutput(follow_up_needed=True, follow_up_question="What specifically failed?")
    with fake_chain("app.agents.nodes.follow_up_decider", result=output):
        updated = await follow_up_decider_node(state)

    assert updated["is_complete"] is False
    assert updated["current_question_index"] == 1
    assert updated["questions"][1]["order_index"] == 4.1
    assert updated["follow_up_count"] == 1


@pytest.mark.asyncio
async def test_follow_up_marks_the_interview_complete_after_the_last_answer() -> None:
    question = {"question_text": "Last", "question_type": "technical", "order_index": 2}
    state = interview_state(
        questions=[dict(question)],
        current_question=dict(question),
        answers=[{"answer_text": "done", "score": 90, "feedback": "good"}],
    )
    with fake_chain(
        "app.agents.nodes.follow_up_decider",
        result=FollowUpDeciderOutput(follow_up_needed=False),
    ):
        updated = await follow_up_decider_node(state)
    assert updated["is_complete"] is True
    assert updated["current_question_index"] == 1


@pytest.mark.asyncio
async def test_missing_score_is_treated_as_zero_and_can_earn_a_follow_up() -> None:
    question = {"question_text": "Q", "question_type": "technical", "order_index": 1}
    state = interview_state(
        questions=[question, {"question_text": "Q2", "question_type": "technical", "order_index": 2}],
        current_question=dict(question),
        answers=[{"answer_text": "um", "feedback": ""}],
    )
    output = FollowUpDeciderOutput(follow_up_needed=True, follow_up_question="Say more.")
    with fake_chain("app.agents.nodes.follow_up_decider", result=output):
        updated = await follow_up_decider_node(state)
    assert updated["questions"][1]["question_text"] == "Say more."
    assert updated["follow_up_count"] == 1


@pytest.mark.asyncio
async def test_follow_up_error_does_not_advance_the_interview() -> None:
    question = {"question_text": "Q", "question_type": "technical", "order_index": 1}
    state = interview_state(
        questions=[question],
        current_question=dict(question),
        current_question_index=0,
        is_complete=False,
        answers=[{"answer_text": "x", "score": 10, "feedback": "weak"}],
    )
    with fake_chain("app.agents.nodes.follow_up_decider", error=RuntimeError("down")):
        updated = await follow_up_decider_node(state)
    assert updated["current_question_index"] == 0
    assert updated["is_complete"] is False
    assert updated["error"].startswith("Error deciding on follow-up question:")


@pytest.mark.asyncio
async def test_follow_up_requires_an_answer() -> None:
    state = interview_state(answers=[], current_question={"question_text": "Q", "order_index": 1})
    with pytest.raises(IndexError):
        await follow_up_decider_node(state)


@pytest.mark.asyncio
async def test_final_evaluator_stores_the_hiring_recommendation() -> None:
    output = FinalEvaluatorOutput(
        communication_score=80,
        technical_score=90,
        problem_solving_score=70,
        overall_score=84,
        verdict=Verdict.STRONG_HIRE,
        improvement_tips=["Quantify the result"],
    )
    state = interview_state(answers=[{"answer_text": "I shipped it", "score": 90, "feedback": "strong"}])
    with fake_chain("app.agents.nodes.final_evaluator", result=output) as chain:
        updated = await final_evaluator_node(state)

    assert updated["final_evaluation"]["verdict"] == Verdict.STRONG_HIRE
    assert updated["final_evaluation"]["overall_score"] == 84
    assert updated["final_evaluation"]["improvement_tips"] == ["Quantify the result"]
    assert chain.ainvoke.await_args.args[0]["questions"] == state["questions"]


@pytest.mark.asyncio
async def test_final_evaluator_records_model_errors() -> None:
    state = interview_state(final_evaluation={"keep": True})
    with fake_chain("app.agents.nodes.final_evaluator", error=RuntimeError("no verdict")):
        updated = await final_evaluator_node(state)
    assert updated["final_evaluation"] == {"keep": True}
    assert updated["error"].startswith("Error evaluating final performance:")
