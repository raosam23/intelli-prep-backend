"""Interview websocket.

The handler opens its own AsyncSession and drives the compiled graph, so both
are replaced. TestClient exercises the socket protocol. The disconnect path is
called directly because closing the TestClient socket also cancels the app
task, which races the disconnect handler.
"""

from contextlib import contextmanager
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.websocket.interview_ws import interview_websocket
from app.models.answer import Answer
from app.models.evaluation import Evaluation, Verdict
from app.models.interview_session import InterviewSession, InterviewStatus
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.question import Question, QuestionType
from app.models.resume import Resume
from app.models.user import User
from app.utils.security import create_access_token
from tests.factories import make_interview, make_job, make_resume, make_user


class FakeDBSession:
    def __init__(self, records: dict[tuple[type, Any], Any] | None = None) -> None:
        self.records = records or {}
        self.added: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    async def get(self, model: type, ident: Any) -> Any:
        return self.records.get((model, ident))

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def flush(self) -> None:
        self.flushes += 1


class ScriptedGraph:
    """Returns scripted checkpoints instead of running the real graph."""

    def __init__(self, snapshots: list[dict[str, Any]]) -> None:
        self.snapshots = snapshots
        self.calls = 0
        self.invocations: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []

    async def ainvoke(self, state: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
        self.invocations.append({"state": state, "config": config})
        return {}

    def get_state(self, config: dict[str, Any] | None = None) -> MagicMock:
        snapshot = MagicMock()
        snapshot.values = self.snapshots[self.calls]
        self.calls += 1
        return snapshot

    def update_state(self, config: dict[str, Any] | None = None, values: dict[str, Any] | None = None) -> None:
        self.updates.append(values or {})


def _snapshot(**overrides: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "fit_score": 81.5,
        "fit_breakdown_score": {"technical_skills_match": 90, "experience_match": 70},
        "parsed_resume": {"skills": ["Python"]},
        "current_question": {
            "question_text": "Design a rate limiter",
            "question_type": "technical",
            "order_index": 1.26,
        },
        "current_question_index": 0,
        "num_questions": 2,
        "is_complete": False,
        "answers": [],
        "questions": [],
        "final_evaluation": {},
    }
    state.update(overrides)
    return state


def _stack(**interview_overrides: Any):
    user = make_user()
    resume = make_resume(user_id=user.id, raw_text="Jane Doe\nBuilt APIs")
    job = make_job(user_id=user.id, resume_id=resume.id, jd_raw_text="Backend engineer")
    interview = make_interview(
        job_application_id=job.id,
        num_questions=2,
        focus_area="apis",
        **interview_overrides,
    )
    records = {
        (InterviewSession, interview.id): interview,
        (JobApplication, job.id): job,
        (Resume, resume.id): resume,
        (User, user.id): user,
    }
    session = FakeDBSession(records)
    token = create_access_token({"sub": str(user.id)})
    return user, resume, job, interview, session, token


def _url(interview_id: Any, token: str) -> str:
    return f"/api/ws/interview/{interview_id}?{urlencode({'token': token})}"


@contextmanager
def _patched(session: FakeDBSession, graph: Any):
    holder = MagicMock()
    holder.__aenter__ = AsyncMock(return_value=session)
    holder.__aexit__ = AsyncMock(return_value=None)
    with (
        patch("app.api.websocket.interview_ws.AsyncSession", return_value=holder),
        patch("app.api.websocket.interview_ws.interview_graph", graph),
    ):
        yield


def _completed_snapshot() -> dict[str, Any]:
    return _snapshot(
        is_complete=True,
        questions=[
            {
                "question_text": "Design a rate limiter",
                "question_type": QuestionType.TECHNICAL,
                "order_index": 1.0,
            },
            {
                "question_text": "Why that limit?",
                "question_type": "followup",
                "order_index": 1.1,
            },
        ],
        answers=[
            {"answer_text": "Token bucket", "score": 88, "feedback": "Clear structure"},
            {"answer_text": "Burst traffic", "score": 74, "feedback": "Good"},
        ],
        final_evaluation={
            "communication_score": 80,
            "technical_score": 90,
            "problem_solving_score": 85,
            "overall_score": 86,
            "verdict": "hire",
            "improvement_tips": ["Quantify latency", "Mention tradeoffs"],
        },
    )


def test_invalid_token_closes_before_accept(client: TestClient) -> None:
    _user, _resume, _job, interview, session, _token = _stack()
    with _patched(session, ScriptedGraph([])):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(_url(interview.id, "not-a-jwt")):
                pass
    assert exc_info.value.code == 4001
    assert session.commits == 0


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (InterviewStatus.COMPLETED, "Interview session already completed"),
        (InterviewStatus.INPROGRESS, "Interview session already in progress"),
    ],
)
def test_socket_refuses_sessions_that_are_not_pending(
    client: TestClient, status: InterviewStatus, message: str
) -> None:
    _user, _resume, _job, interview, session, token = _stack(status=status)
    graph = ScriptedGraph([])
    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            assert websocket.receive_json() == {"error": message}
    assert graph.invocations == []
    assert interview.status == status


@pytest.mark.parametrize(
    ("drop", "message"),
    [
        ("interview", "Interview session not found"),
        ("job", "Job application not found"),
        ("resume", "Resume not found"),
        ("user", "User not found"),
    ],
)
def test_socket_reports_missing_records(client: TestClient, drop: str, message: str) -> None:
    _user, resume, job, interview, session, token = _stack()
    if drop == "interview":
        session.records.pop((InterviewSession, interview.id))
    elif drop == "job":
        session.records.pop((JobApplication, job.id))
    elif drop == "resume":
        session.records.pop((Resume, resume.id))
    else:
        session.records.pop((User, _user.id))
    graph = ScriptedGraph([])
    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            assert websocket.receive_json() == {"error": message}
    assert graph.invocations == []
    if drop != "interview":
        assert interview.status == InterviewStatus.PENDING


def test_socket_runs_a_question_then_persists_the_evaluation(client: TestClient) -> None:
    _user, resume, job, interview, session, token = _stack()
    graph = ScriptedGraph([_snapshot(is_complete=False), _completed_snapshot()])

    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            fit = websocket.receive_json()
            question = websocket.receive_json()
            websocket.send_json({"type": "ping"})
            websocket.send_json({"type": "answer", "answer": "Token bucket"})
            evaluation = websocket.receive_json()

    assert fit == {
        "type": "fit_score",
        "fit_score": 81.5,
        "fit_breakdown": {"technical_skills_match": 90, "experience_match": 70},
    }
    assert question["type"] == "question"
    assert question["question_number"] == 1
    assert question["total_questions"] == 2
    assert question["question"]["order_index"] == 1.3
    assert question["question"]["question_text"] == "Design a rate limiter"
    assert evaluation["type"] == "evaluation"
    assert evaluation["final_evaluation"]["verdict"] == "hire"

    initial = graph.invocations[0]
    assert initial["state"]["raw_resume"] == "Jane Doe\nBuilt APIs"
    assert initial["state"]["jd_raw_text"] == "Backend engineer"
    assert initial["state"]["num_questions"] == 2
    assert initial["state"]["focus_area"] == "apis"
    assert initial["config"]["configurable"]["thread_id"] == str(interview.id)
    assert graph.updates[0]["error"] is None
    assert graph.updates[0]["answers"] == [{"answer_text": "Token bucket", "score": None, "feedback": None}]

    questions = [row for row in session.added if isinstance(row, Question)]
    answers = [row for row in session.added if isinstance(row, Answer)]
    evaluations = [row for row in session.added if isinstance(row, Evaluation)]
    assert [row.question_text for row in questions] == ["Design a rate limiter", "Why that limit?"]
    assert questions[0].is_follow_up is False
    assert questions[0].question_type == QuestionType.TECHNICAL
    assert questions[1].is_follow_up is True
    assert questions[1].question_type == QuestionType.FOLLOWUP
    assert questions[1].follow_up_to is None
    assert [row.answer_text for row in answers] == ["Token bucket", "Burst traffic"]
    assert answers[0].score == 88
    assert answers[0].audio_file_path is None
    assert evaluations[0].verdict == Verdict.HIRE
    assert evaluations[0].overall_score == 86
    assert json.loads(evaluations[0].improvement_tips_json) == ["Quantify latency", "Mention tradeoffs"]
    assert interview.status == InterviewStatus.COMPLETED
    assert interview.feedback == "Quantify latency\nMention tradeoffs"
    assert job.status == ApplicationStatus.APPROVED
    assert job.fit_score == 81.5
    assert json.loads(job.fit_breakdown_score)["technical_skills_match"] == 90
    assert json.loads(resume.parsed_json) == {"skills": ["Python"]}
    assert session.flushes == 1


@pytest.mark.parametrize(
    ("verdict", "expected_status"),
    [
        ("strong_hire", ApplicationStatus.APPROVED),
        ("no_hire", ApplicationStatus.REJECTED),
        ("strong_no_hire", ApplicationStatus.REJECTED),
        ("no_decision", ApplicationStatus.INTERVIEWING),
    ],
)
def test_verdict_updates_the_job_application_status(
    client: TestClient, verdict: str, expected_status: ApplicationStatus
) -> None:
    _user, _resume, job, interview, session, token = _stack()
    finished = _completed_snapshot()
    finished["final_evaluation"] = {**finished["final_evaluation"], "verdict": verdict, "improvement_tips": []}
    graph = ScriptedGraph([_snapshot(is_complete=False), finished])

    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json({"type": "answer", "answer": "answer"})
            message = websocket.receive_json()

    assert message["final_evaluation"]["verdict"] == verdict
    assert job.status == expected_status
    assert interview.status == InterviewStatus.COMPLETED


def test_socket_sends_the_next_question_until_the_interview_is_complete(client: TestClient) -> None:
    _user, _resume, _job, interview, session, token = _stack()
    second = _snapshot(
        is_complete=False,
        current_question_index=1,
        current_question={"question_text": "How do you test APIs?", "question_type": "technical", "order_index": 2},
        answers=[{"answer_text": "first", "score": 70, "feedback": "ok"}],
    )
    graph = ScriptedGraph([_snapshot(is_complete=False), second, _completed_snapshot()])

    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            websocket.receive_json()
            first = websocket.receive_json()
            websocket.send_json({"type": "answer", "answer": "first"})
            nxt = websocket.receive_json()
            websocket.send_json({"type": "answer", "answer": "second"})
            done = websocket.receive_json()

    assert first["question_number"] == 1
    assert nxt["type"] == "question"
    assert nxt["question_number"] == 2
    assert nxt["question"]["question_text"] == "How do you test APIs?"
    assert nxt["question"]["order_index"] == 2.0
    assert graph.updates[1]["answers"][-1]["answer_text"] == "second"
    assert done["type"] == "evaluation"
    assert interview.status == InterviewStatus.COMPLETED


def test_socket_reports_a_graph_failure_and_marks_the_session_incomplete(client: TestClient) -> None:
    _user, _resume, job, interview, session, token = _stack()

    class BoomGraph(ScriptedGraph):
        async def ainvoke(self, state: Any, config: dict[str, Any] | None = None) -> dict[str, Any]:
            raise RuntimeError("model unavailable")

    with _patched(session, BoomGraph([])):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            message = websocket.receive_json()

    assert message["type"] == "error"
    assert "model unavailable" in message["message"]
    assert interview.status == InterviewStatus.INCOMPLETE
    assert job.status == ApplicationStatus.APPLIED
    assert session.rollbacks == 1


def test_socket_reports_a_failure_while_saving_the_transcript(client: TestClient) -> None:
    """`mixed` is an interview type, not a question type, so persistence fails closed."""
    _user, _resume, job, interview, session, token = _stack()
    finished = _completed_snapshot()
    finished["questions"] = [{"question_text": "Q", "question_type": "mixed", "order_index": 1.0}]
    finished["answers"] = [{"answer_text": "A", "score": 50, "feedback": "ok"}]
    graph = ScriptedGraph([_snapshot(is_complete=False), finished])

    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json({"type": "answer", "answer": "A"})
            message = websocket.receive_json()

    assert message["type"] == "error"
    assert interview.status == InterviewStatus.INCOMPLETE
    assert job.status == ApplicationStatus.APPLIED
    assert session.rollbacks == 1


def test_question_without_an_order_index_is_forwarded_unchanged(client: TestClient) -> None:
    _user, _resume, _job, interview, session, token = _stack()
    opening = _snapshot(current_question={"question_text": "Tell me about yourself", "question_type": "behavioral"})
    graph = ScriptedGraph([opening, _completed_snapshot()])

    with _patched(session, graph):
        with client.websocket_connect(_url(interview.id, token)) as websocket:
            websocket.receive_json()
            question = websocket.receive_json()
            websocket.send_json({"type": "answer", "answer": "I like building APIs"})
            websocket.receive_json()

    assert "order_index" not in question["question"]
    assert question["question"]["question_text"] == "Tell me about yourself"


@pytest.mark.asyncio
async def test_client_disconnect_marks_the_session_incomplete() -> None:
    _user, _resume, job, interview, session, token = _stack()
    graph = ScriptedGraph([_snapshot(is_complete=False)])
    websocket = AsyncMock()
    websocket.receive_json.side_effect = WebSocketDisconnect()

    with _patched(session, graph):
        await interview_websocket(websocket, interview.id, token)

    assert interview.status == InterviewStatus.INCOMPLETE
    assert job.status == ApplicationStatus.APPLIED
    assert session.rollbacks == 1
    assert session.commits >= 1
    websocket.accept.assert_awaited()
    websocket.close.assert_awaited()
    sent_types = [call.args[0]["type"] for call in websocket.send_json.await_args_list]
    assert sent_types == ["fit_score", "question"]
