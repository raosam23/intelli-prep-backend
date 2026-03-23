from langgraph.graph import StateGraph, END, START
from app.agents.should_continue import should_continue
from app.agents.nodes.resume_parser import resume_parser_node
from app.agents.nodes.question_generator import question_generator_node
from app.agents.nodes.jd_analyzer import jd_analyzer_node
from app.agents.nodes.interview_loop import interview_loop_node
from app.agents.nodes.follow_up_decider import follow_up_decider_node
from app.agents.nodes.fit_scorer import fit_scorer_node
from app.agents.nodes.final_evaluator import final_evaluator_node
from app.agents.nodes.answer_evaluator import answer_evaluator_node
from app.agents.state import InterviewState

graph = StateGraph(InterviewState)

graph.add_node("resume_parser", resume_parser_node)
graph.add_node("question_generator", question_generator_node)
graph.add_node("jd_analyzer", jd_analyzer_node)
graph.add_node("interview_loop", interview_loop_node)
graph.add_node("follow_up_decider", follow_up_decider_node)
graph.add_node("fit_scorer", fit_scorer_node)
graph.add_node("final_evaluator", final_evaluator_node)
graph.add_node("answer_evaluator", answer_evaluator_node)

graph.add_edge(START, "resume_parser")
graph.add_edge("resume_parser", "jd_analyzer")
graph.add_edge("jd_analyzer", "fit_scorer")
graph.add_edge("fit_scorer", "question_generator")
graph.add_edge("question_generator", "interview_loop")
graph.add_edge("interview_loop", "answer_evaluator")
graph.add_edge("answer_evaluator", "follow_up_decider")
graph.add_conditional_edges("follow_up_decider", should_continue, {
    "interview_loop": "interview_loop",
    "final_evaluator": "final_evaluator"
})
graph.add_edge("final_evaluator", END)

interview_graph = graph.compile()