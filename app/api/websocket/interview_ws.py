from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine
from app.agents.state import InterviewState
from app.agents.graph import interview_graph
from app.models.interview_session import InterviewSession, InterviewStatus
from app.models.evaluation import Evaluation, Verdict
from app.models.question import Question, QuestionType
from app.models.answer import Answer
from app.models.job_application import ApplicationStatus, JobApplication
from app.models.resume import Resume
from app.models.user import User
from app.utils.security import decode_access_token
from langchain_core.runnables.config import RunnableConfig
from langgraph.types import StateSnapshot
from typing import cast
from datetime import datetime, timezone
import uuid
import json

router = APIRouter()

@router.websocket("/api/ws/interview/{session_id}")
async def interview_websocket(websocket: WebSocket, session_id: uuid.UUID, token: str = Query(...)):
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    await websocket.accept()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        interview = await session.get(InterviewSession, session_id)
        if not interview:
            await websocket.send_json({"error": "Interview session not found"})
            await websocket.close()
            return
        if interview.status == InterviewStatus.COMPLETED:
            await websocket.send_json({"error": "Interview session already completed"})
            await websocket.close()
            return
        if interview.status == InterviewStatus.INPROGRESS:
            await websocket.send_json({"error": "Interview session already in progress"})
            await websocket.close()
            return
        job_application = await session.get(JobApplication, interview.job_application_id)
        if not job_application:
            await websocket.send_json({"error": "Job application not found"})
            await websocket.close()
            return
        resume = await session.get(Resume, job_application.resume_id)
        if not resume:
            await websocket.send_json({"error": "Resume not found"})
            await websocket.close()
            return
        user = await session.get(User, job_application.user_id)
        if not user:
            await websocket.send_json({"error": "User not found"})
            await websocket.close()
            return

        state: InterviewState = {
            "session_id": str(session_id),
            "user_id": str(user.id),
            "job_application_id": str(job_application.id),
            "raw_resume": resume.raw_text or "",
            "parsed_resume": {},
            "jd_raw_text": job_application.jd_raw_text or "",
            "parsed_jd": {},
            "fit_score": 0.0,
            "fit_breakdown_score": {},
            "num_questions": interview.num_questions,
            "difficulty": interview.difficulty,
            "interview_type": interview.interview_type,
            "focus_area": interview.focus_area,
            "questions": [],
            "current_question_index": 0,
            "current_question": {},
            "answers": [],
            "follow_up_count": 0,
            "final_evaluation": {},
            "is_complete": False,
            "error": None,
        }

        interview.status = InterviewStatus.INPROGRESS
        await session.commit()

        try:
            config: RunnableConfig = {"configurable": {"thread_id": str(session_id)}}
            await interview_graph.ainvoke(state, config=config)
            snapshot: StateSnapshot = interview_graph.get_state(config=config)
            current_state: InterviewState = cast(InterviewState, snapshot.values)
            await websocket.send_json({
                "type": "fit_score",
                "fit_score": current_state['fit_score'],
                "fit_breakdown": current_state['fit_breakdown_score']
            })
            job_application.fit_score = float(current_state.get('fit_score', 0.0))
            job_application.fit_breakdown_score = json.dumps(current_state.get('fit_breakdown_score', {}))
            job_application.status = ApplicationStatus.INTERVIEWING
            job_application.updated_at = datetime.now(timezone.utc)
            resume.parsed_json = json.dumps(current_state.get('parsed_resume', {}))
            resume.updated_at = datetime.now(timezone.utc)
            session.add(job_application)
            session.add(resume)
            await session.commit()
            current_question = dict(current_state["current_question"])
            if "order_index" in current_question:
                current_question["order_index"] = round(float(current_question["order_index"]), 1)
            await websocket.send_json({
                "type": "question",
                "question": current_question,
                "question_number": current_state['current_question_index'] + 1,
                "total_questions": current_state['num_questions']
            })
            while not current_state['is_complete']:
                data = await websocket.receive_json()
                if data['type'] != 'answer':
                    continue
                interview_graph.update_state(config=config, values={
                    "answers": current_state["answers"] + [{
                        "answer_text": data["answer"],
                        "score": None,
                        "feedback": None
                    }],
                    "error": None
                })
                await interview_graph.ainvoke(None, config=config)
                snapshot = interview_graph.get_state(config=config)
                current_state = cast(InterviewState, snapshot.values)
                if current_state['is_complete']:
                    final_evaluation = current_state['final_evaluation']
                    db_questions = []
                    for question in current_state['questions']:
                        raw_order = float(question.get('order_index', 0))
                        is_follow_up = not raw_order.is_integer()
                        raw_type = question.get("question_type", QuestionType.TECHNICAL)
                        if isinstance(raw_type, QuestionType):
                            question_type = raw_type
                        else:
                            question_type = QuestionType(raw_type)
                        db_question = Question(
                            session_id=session_id,
                            question_text=question['question_text'],
                            question_type=question_type,
                            order_index=raw_order,
                            is_follow_up=is_follow_up,
                            follow_up_to=None, #TODO: delete this from the database later, it is useless
                            created_at= datetime.now(timezone.utc)
                        )
                        session.add(db_question)
                        db_questions.append(db_question)
                    await session.flush()

                    for db_question, answer in zip(db_questions, current_state['answers']):
                        db_answer = Answer(
                            question_id=db_question.id,
                            session_id=session_id,
                            answer_text=answer.get('answer_text'),
                            audio_file_path=None,
                            score=answer.get('score'),
                            feedback=answer.get('feedback'),
                            created_at= datetime.now(timezone.utc)
                        )
                        session.add(db_answer)

                    evaluation = Evaluation(
                        session_id=session_id,
                        communication_score=final_evaluation.get('communication_score'),
                        technical_score=final_evaluation.get('technical_score'),
                        problem_solving_score=final_evaluation.get('problem_solving_score'),
                        overall_score=final_evaluation.get('overall_score'),
                        verdict=Verdict(final_evaluation.get('verdict', 'no_decision')),
                        improvement_tips_json=json.dumps(final_evaluation.get('improvement_tips', []))
                    )
                    session.add(evaluation)
                    interview.status = InterviewStatus.COMPLETED
                    interview.feedback  = "\n".join(final_evaluation.get('improvement_tips', []))
                    interview.updated_at = datetime.now(timezone.utc)
                    session.add(interview)
                    if final_evaluation.get('verdict') in [Verdict.HIRE, Verdict.STRONG_HIRE]:
                        job_application.status = ApplicationStatus.APPROVED
                        job_application.updated_at = datetime.now(timezone.utc)
                    elif final_evaluation.get('verdict') in [Verdict.NO_HIRE, Verdict.STRONG_NO_HIRE]:
                        job_application.status = ApplicationStatus.REJECTED
                        job_application.updated_at = datetime.now(timezone.utc)
                    session.add(job_application)
                    await session.commit()
                    await websocket.send_json({
                        "type": "evaluation",
                        "final_evaluation": final_evaluation
                    })
                    break
                else:
                    current_question = dict(current_state["current_question"])
                    if "order_index" in current_question:
                        current_question["order_index"] = round(float(current_question["order_index"]), 1)
                    await websocket.send_json({
                        "type": "question",
                        "question": current_question,
                        "question_number": current_state['current_question_index'] + 1,
                        "total_questions": current_state['num_questions']
                    })
        except WebSocketDisconnect:
            await session.rollback()
            interview.status = InterviewStatus.INCOMPLETE
            job_application.status = ApplicationStatus.APPLIED
            await session.commit()
        except Exception as e:
            await session.rollback()
            interview.status = InterviewStatus.INCOMPLETE
            job_application.status = ApplicationStatus.APPLIED
            await session.commit()
            await websocket.send_json({
                "type": "error",
                "message": f"An error occurred during the interview process: {str(e)}"
            })
        finally:
            await websocket.close()
