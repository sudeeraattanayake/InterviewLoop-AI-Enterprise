from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)
    role: str
    company_name: str = Field(default='', max_length=150)
    email_opt_in: bool = False

    @field_validator('role')
    @classmethod
    def role_check(cls, value):
        if value not in ('recruiter', 'candidate'):
            raise ValueError('Invalid role')
        return value


class LoginIn(BaseModel):
    email: str
    password: str


class JobIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    department: str = Field(default='Engineering', max_length=100)
    location: str = Field(default='Remote', max_length=160)
    employment_type: str = Field(default='Full-time', max_length=50)
    description: str = Field(min_length=20, max_length=25000)
    requirements: list[str] = Field(min_length=1, max_length=18)

    @field_validator('requirements')
    @classmethod
    def requirements_check(cls, items):
        clean = [s.strip()[:160] for s in items if s.strip()]
        if not clean:
            raise ValueError('At least one requirement is needed')
        return list(dict.fromkeys(clean))


class DecisionIn(BaseModel):
    decision: str  # advance / decline / revise / approve
    notes: str = Field(default='', max_length=4000)


class ScheduleIn(BaseModel):
    starts_at: str = Field(min_length=10, max_length=50)
    meeting_link: str = Field(default='', max_length=500)
    notes: str = Field(default='', max_length=4000)


class FinalDecisionIn(BaseModel):
    outcome: str  # offer / reject
    notes: str = Field(min_length=10, max_length=4000)
    rubric: dict[str, str] = Field(default_factory=dict)


class PreferencesIn(BaseModel):
    video_consent: bool


class TranscriptIn(BaseModel):
    transcript: str = Field(min_length=1, max_length=12000)


class OrganizationIn(BaseModel):
    name: str = Field(min_length=3, max_length=150)

class JoinOrganizationIn(BaseModel):
    invite_code: str = Field(min_length=12, max_length=80)

class ChallengeIn(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    prompt: str = Field(min_length=20, max_length=10000)
    language: str = 'python'
    starter_code: str = Field(default='', max_length=12000)
    cases: list[dict] = Field(default_factory=list, max_length=12)

    @field_validator('language')
    @classmethod
    def language_valid(cls, value):
        if value not in ('python', 'javascript'):
            raise ValueError('Supported languages: python and javascript')
        return value

    @field_validator('cases')
    @classmethod
    def cases_valid(cls, items):
        for item in items:
            if not isinstance(item.get('input'), str) or not isinstance(item.get('expected'), str):
                raise ValueError('Each case needs string input and expected')
            if len(item['input']) > 2000 or len(item['expected']) > 2000:
                raise ValueError('Test case too long')
        return items

class CodeIn(BaseModel):
    source_code: str = Field(min_length=5, max_length=24000)

class CommentIn(BaseModel):
    body: str = Field(min_length=2, max_length=3000)

class CodeReviewIn(BaseModel):
    decision: str
    notes: str = Field(min_length=10, max_length=4000)

class OfferReplyIn(BaseModel):
    response: str

class OfferTermsIn(BaseModel):
    terms: str = Field(min_length=5, max_length=3000)

class PreferenceIn(BaseModel):
    email_opt_in: bool
