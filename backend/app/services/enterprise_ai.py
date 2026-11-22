"""Optional remote integrations. Never executes untrusted candidate code locally."""
import hashlib
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from ..config import get_settings

settings = get_settings()


def voice_session_secret(application_id: int, candidate_id: int, title: str, questions: list[str]):
    if not settings.openai_api_key:
        raise HTTPException(503, 'OPENAI_API_KEY is required for live AI voice. Recorded interview works offline.')
    instructions = (
        f'You are a respectful structured voice interviewer for the role: {title[:120]}. '
        'This is a practice-like job interview, not a hiring decision. Use only job-related questions. '
        'Ask one question at a time from the supplied list, then at most one clarifying follow-up per question. '
        'Never ask for protected characteristics, personal life, age, citizenship, medical information, '
        'disabilities, family plans, or passwords. Do not assess accent, appearance, emotion, confidence, '
        'truthfulness, or personality. No evaluation score, hire or reject advice. '
        'Speak clearly, let the candidate finish, and allow repetition and pauses. '
        'If the interviewee requests accessibility accommodation, comply where feasible. '
        'Questions:\n' + '\n'.join(f'{i+1}. {x[:650]}' for i,x in enumerate(questions[:6]))
    )
    hashed = hashlib.sha256(f'{candidate_id}:{settings.secret_key}'.encode()).hexdigest()[:32]
    try:
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            response = client.post('https://api.openai.com/v1/realtime/client_secrets',
                headers={'Authorization': f'Bearer {settings.openai_api_key}', 'OpenAI-Safety-Identifier': hashed},
                json={'session': {'type':'realtime', 'model':settings.realtime_model,
                      'instructions':instructions,
                      'audio': {'input': {'transcription': {'model':'gpt-4o-mini-transcribe'}},
                                'output': {'voice':'marin'}}}})
        response.raise_for_status()
        data = response.json()
        return {'value':data['value'], 'model':settings.realtime_model, 'expires_at':data.get('expires_at')}
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(502, f'Realtime provider is unavailable: {type(exc).__name__}') from exc


def run_remote_tests(source_code: str, language: str, cases: list[dict]) -> dict:
    """Only calls an explicitly configured trusted isolated Judge0 instance via HTTPS."""
    base = settings.judge0_url.strip().rstrip('/')
    if not base:
        return {'status':'manual_review', 'detail':'No isolated Judge0 execution provider configured; code saved for human review.', 'tested':0}
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
        raise HTTPException(503, 'JUDGE0_URL must be a trusted HTTPS endpoint')
    language_id = {'python':71, 'javascript':63}.get(language)
    if not language_id:
        raise HTTPException(422, 'Unsupported language')
    headers={'Content-Type':'application/json'}
    if settings.judge0_api_key:
        headers['X-RapidAPI-Key']=settings.judge0_api_key
    if settings.judge0_api_host:
        headers['X-RapidAPI-Host']=settings.judge0_api_host
    passed = 0
    executed = 0
    errors = []
    try:
        with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client:
            for case in cases[:12]:
                response=client.post(base+'/submissions', params={'wait':'true', 'base64_encoded':'false'}, headers=headers,
                   json={'source_code':source_code, 'language_id':language_id,
                         'stdin':case['input'], 'expected_output':case['expected'],
                         'cpu_time_limit':2, 'wall_time_limit':5, 'memory_limit':128000,
                         'max_file_size':1024})
                response.raise_for_status()
                data=response.json()
                status_id=(data.get('status') or {}).get('id')
                if status_id in (1,2) or data.get('token') and status_id is None:
                    errors.append('Remote provider returned a queued submission; enable wait support')
                    break
                executed+=1
                if status_id==3:
                    passed+=1
                elif status_id is None:
                    errors.append('Execution provider did not return a status')
                    break
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        errors.append(f'Isolated executor unavailable: {type(exc).__name__}')
    status='completed' if executed==len(cases) and not errors else 'partial_or_unavailable'
    return {'status':status, 'passed':passed, 'tested':executed, 'total':len(cases),
            'detail':'Automated tests are technical evidence for human review, not a hiring verdict.',
            'errors':errors[:2]}
