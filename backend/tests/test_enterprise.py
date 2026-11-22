"""Provider-free enterprise unit tests. For real LangGraph workflows run enterprise_smoke_test.py."""
from types import SimpleNamespace
from pydantic import ValidationError
from app.schemas import ChallengeIn, CodeIn, CommentIn
from app.services.reporting import create_report
from app.services.enterprise_ai import run_remote_tests


def test_challenge_requires_supported_language():
    try:
        ChallengeIn(title='Logic task',prompt='Explain a real problem and write a correct program.',language='bash')
    except ValidationError:
        pass
    else:
        raise AssertionError('Unsafe language accepted')


def test_challenge_rejects_missing_test_fields():
    try:
        ChallengeIn(title='Logic task',prompt='Explain a real problem and write a correct program.',cases=[{'input':'hi'}])
    except ValidationError:
        pass
    else:
        raise AssertionError('Incomplete hidden test accepted')


def test_coding_payload_is_size_limited():
    try:
        CodeIn(source_code='x'*30000)
    except ValidationError:
        pass
    else:
        raise AssertionError('Oversized source accepted')


def test_comment_cannot_be_empty():
    try:
        CommentIn(body='')
    except ValidationError:
        pass
    else:
        raise AssertionError('Empty reviewer note accepted')


def test_no_local_candidate_code_execution():
    x=run_remote_tests('print(999)', 'python',[{'input':'1 2','expected':'3\n'}])
    assert x['status']=='manual_review' and x['tested']==0


def test_real_pdf_generation_does_not_require_openai():
    job=SimpleNamespace(title='Junior AI Engineer')
    user=SimpleNamespace(name='Synthetic Person',email='synthetic@example.test')
    application=SimpleNamespace(id=7,job=job,stage='awaiting_cv_review',candidate=user,
         cv_review={'mode':'local_rules','items':[{'requirement':'Python','excerpt':'Python API project'}]},
         video_review={},interview_datetime='',recruiter_notes='',individual_feedback={})
    pdf=create_report(application,[],candidate_view=True,outline={'summary':'Facts only','items':[]})
    assert pdf.startswith(b'%PDF') and len(pdf)>1000
