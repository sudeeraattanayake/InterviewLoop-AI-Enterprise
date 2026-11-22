"""Durable LangGraph subgraphs with real interrupt()/Command(resume=...) HITL gates."""
import sqlite3
from threading import RLock
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from typing_extensions import TypedDict
from ..config import get_settings
from .ai import analyze_cv, generate_questions, analyze_video


class FlowState(TypedDict, total=False):
    job: dict
    resume: str
    consent: bool
    questions: list[dict]
    review: dict
    decision: dict
    step: str
    execution: dict
    source: str
    language: str
    report_data: dict


def cv_node(state: FlowState):
    return {'review': analyze_cv(state['job'], state['resume'], state.get('consent', False)), 'step': 'cv_evidence_prepared'}


def questions_node(state: FlowState):
    return {'review': generate_questions(state['job'], state.get('consent', False)), 'step': 'questions_prepared'}


def video_node(state: FlowState):
    return {'review': analyze_video(state['questions'], state.get('consent', False)), 'step': 'video_evidence_prepared'}


def verify_node(state: FlowState):
    # A substantive machine validation boundary, not a second LLM.
    if not isinstance(state.get('review'), dict) or not state['review']:
        raise ValueError('Cannot advance a workflow without evidence')
    return {'step': 'ready_for_human_review'}


def human_gate(state: FlowState):
    # Interrupt state persists in SQLite, survives API process restarts.
    decision = interrupt({'type': 'recruiter_approval', 'stage': state['step'], 'review': state['review']})
    if not isinstance(decision, dict) or decision.get('decision') not in ('advance', 'decline'):
        raise ValueError('A human must explicitly decide advance or decline')
    return {'decision': decision, 'step': 'human_decision_recorded'}


def code_node(state: FlowState):
    execution = state.get('execution') or {}
    review = {
        'mode': 'deterministic_technical_evidence',
        'summary': 'Code has been saved for a recruiter to review. Execution results are technical evidence only.',
        'items': [
            {'skill': 'Language', 'observation': state.get('language','unknown')},
            {'skill': 'Submitted source', 'observation': f"{len(state.get('source',''))} source characters stored for review"},
            {'skill': 'Isolated test execution', 'observation':
                f"{execution.get('status','not_run')}: {execution.get('passed',0)}/{execution.get('tested',0)} tests passed (of {execution.get('total',0)} configured)"}
        ],
        'limitations': ['Tests do not establish candidate capability on their own', 'Human technical review is required']
    }
    return {'review':review, 'step':'code_evidence_prepared'}


def report_node(state: FlowState):
    info = state.get('report_data') or {}
    review = {
        'mode':'factual_report_assembly',
        'summary': f"Evidence packet assembled for application {info.get('application_id')}, stage: {info.get('stage')}",
        'items': [
            {'skill':'CV criteria', 'observation':f"{info.get('criteria_count',0)} requirements recorded"},
            {'skill':'Video answers', 'observation':f"{info.get('video_answers',0)} candidate transcripts recorded"},
            {'skill':'Technical task', 'observation':info.get('coding_status','Not assigned')},
            {'skill':'Hiring authority', 'observation':'Final decision belongs to a documented human reviewer'}
        ]
    }
    return {'review':review, 'step':'report_sections_prepared'}


def subgraph(node):
    g = StateGraph(FlowState)
    g.add_node('analyze', node)
    g.add_node('verify', verify_node)
    g.add_edge(START, 'analyze')
    g.add_edge('analyze', 'verify')
    g.add_edge('verify', END)
    return g.compile()


cv_subgraph = subgraph(cv_node)
video_subgraph = subgraph(video_node)
question_subgraph = subgraph(questions_node)
code_subgraph = subgraph(code_node)
report_subgraph = subgraph(report_node)


def parent_graph(child):
    g = StateGraph(FlowState)
    # The compiled subgraph is a real LangGraph graph node.
    g.add_node('evidence_subgraph', child)
    g.add_node('human_gate', human_gate)
    g.add_edge(START, 'evidence_subgraph')
    g.add_edge('evidence_subgraph', 'human_gate')
    g.add_edge('human_gate', END)
    return g


settings = get_settings()
_conn = sqlite3.connect(str(settings.root / 'checkpoints.sqlite'), check_same_thread=False)
checkpointer = SqliteSaver(_conn)
cv_graph = parent_graph(cv_subgraph).compile(checkpointer=checkpointer)
video_graph = parent_graph(video_subgraph).compile(checkpointer=checkpointer)
code_graph = parent_graph(code_subgraph).compile(checkpointer=checkpointer)
workflow_lock = RLock()


def start_cv(app_id: int, job: dict, resume: str, consent: bool) -> dict:
    with workflow_lock:
        result = cv_graph.invoke({'job': job, 'resume': resume, 'consent': consent}, config={'configurable': {'thread_id': f'cv-{app_id}'}})
        return result['review']


def resume_cv(app_id: int, decision: str, notes: str) -> dict:
    with workflow_lock:
        result = cv_graph.invoke(Command(resume={'decision': decision, 'notes': notes}), config={'configurable': {'thread_id': f'cv-{app_id}'}})
        return result.get('decision', {})


def questions_for(job: dict, consent: bool) -> dict:
    return question_subgraph.invoke({'job': job, 'consent': consent})['review']


def start_video(app_id: int, answers: list[dict], consent: bool) -> dict:
    with workflow_lock:
        result = video_graph.invoke({'questions': answers, 'consent': consent}, config={'configurable': {'thread_id': f'video-{app_id}'}})
        return result['review']


def resume_video(app_id: int, decision: str, notes: str) -> dict:
    with workflow_lock:
        result = video_graph.invoke(Command(resume={'decision': decision, 'notes': notes}), config={'configurable': {'thread_id': f'video-{app_id}'}})
        return result.get('decision', {})



def start_code(app_id: int, source: str, language: str, execution: dict) -> dict:
    with workflow_lock:
        result = code_graph.invoke({'source':source, 'language':language, 'execution':execution},
            config={'configurable': {'thread_id': f'code-{app_id}'}})
        return result['review']


def resume_code(app_id: int, decision: str, notes: str) -> dict:
    with workflow_lock:
        result = code_graph.invoke(Command(resume={'decision':decision, 'notes':notes}),
            config={'configurable': {'thread_id': f'code-{app_id}'}})
        return result.get('decision',{})


def report_sections(report_data: dict) -> dict:
    """Structured factual report subgraph. No automatic assessment, ranking or recommendation."""
    return report_subgraph.invoke({'report_data':report_data})['review']
