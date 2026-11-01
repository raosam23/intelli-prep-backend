"""Compiled interview graph: node order, conditional edges, and the answer interrupt."""

from app.agents.graph import interview_graph
from app.agents.should_continue import should_continue
from app.core.llm import llm
from tests.factories import interview_state


EXPECTED_EDGES = {
    ("__start__", "resume_parser", False),
    ("resume_parser", "jd_analyzer", False),
    ("jd_analyzer", "fit_scorer", False),
    ("fit_scorer", "question_generator", False),
    ("question_generator", "interview_loop", False),
    ("interview_loop", "answer_evaluator", False),
    ("answer_evaluator", "follow_up_decider", False),
    ("follow_up_decider", "interview_loop", True),
    ("follow_up_decider", "final_evaluator", True),
    ("final_evaluator", "__end__", False),
}


def test_should_continue_routes_to_the_next_question_or_the_final_evaluation() -> None:
    assert should_continue(interview_state(is_complete=False)) == "interview_loop"
    assert should_continue(interview_state(is_complete=True)) == "final_evaluator"


def test_compiled_graph_matches_the_interview_workflow() -> None:
    drawable = interview_graph.get_graph()
    assert set(drawable.nodes) == {
        "__start__",
        "resume_parser",
        "jd_analyzer",
        "fit_scorer",
        "question_generator",
        "interview_loop",
        "answer_evaluator",
        "follow_up_decider",
        "final_evaluator",
        "__end__",
    }
    edges = {(edge.source, edge.target, edge.conditional) for edge in drawable.edges}
    assert edges == EXPECTED_EDGES


def test_graph_pauses_before_scoring_an_answer() -> None:
    """The websocket collects an answer while the graph is interrupted here."""
    assert interview_graph.interrupt_before_nodes == ["answer_evaluator"]
    assert interview_graph.interrupt_after_nodes == []


def test_chat_model_is_deterministic() -> None:
    assert llm.model_name == "gpt-4o-mini"
    assert llm.temperature == 0
