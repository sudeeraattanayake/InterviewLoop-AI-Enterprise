from app.services.ai import rule_based_cv, local_video
from app.schemas import JobIn


def test_conservative_fallback():
    review = rule_based_cv(['Python and FastAPI', 'Kubernetes'], 'I have Python experience', 'test')
    assert review['items'][0]['status'] == 'unclear'
    assert review['items'][1]['status'] == 'not_evidenced'
    assert review['mode'] == 'local_rules'


def test_video_fallback_not_scored():
    x = local_video([{'skill': 'Python', 'transcript': 'I built a service'}], 'test')
    assert 'score' not in x
    assert x['mode'] == 'local_rules'


def test_job_requirements_deduplicated():
    job = JobIn(title='AI Engineer', description='A great role with lots of opportunities.', requirements=[' Python ', 'Python'])
    assert job.requirements == ['Python']
