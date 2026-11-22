"""On-demand PDF evidence packet. Human assessments remain explicitly identified."""
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
from xml.sax.saxutils import escape


def create_report(application, questions, candidate_view=False, outline=None):
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=50,leftMargin=50,topMargin=50,bottomMargin=55,
                          title=f'InterviewLoop evidence #{application.id}')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BigIL',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=23,leading=29,textColor=colors.HexColor('#402b92'),spaceAfter=10))
    styles.add(ParagraphStyle(name='SectionIL',parent=styles['Heading2'],fontSize=12,leading=16,textColor=colors.HexColor('#342f60'),spaceBefore=16,spaceAfter=5))
    styles.add(ParagraphStyle(name='TextIL',parent=styles['BodyText'],fontSize=9.4,leading=14,spaceAfter=6))
    story=[]
    add=lambda text,sty='TextIL':story.append(Paragraph(escape(str(text or '')[:5000]).replace('\n','<br/>'),styles[sty]))
    add('INTERVIEWLOOP / EVIDENCE PACKET','BigIL')
    add(f'Application #{application.id}  |  {application.job.title}  |  {application.stage.replace("_"," ")}')
    add('Generated from current workspace records. Not a hiring recommendation, identity verification, attention analysis, or automatic selection. Recruiter decisions require documented human review.')
    story.append(HRFlowable(width='100%',thickness=1,color=colors.HexColor('#d9d5e7')))
    if outline:
        add('Factual workflow outline (LangGraph report subgraph)','SectionIL')
        add(outline.get('summary',''))
        for item in outline.get('items',[]):
            add(f"{item.get('skill')}: {item.get('observation')}")
    add('Candidate','SectionIL');add(application.candidate.name);add(application.candidate.email)
    add('CV evidence','SectionIL')
    cv=application.cv_review or {}
    add('Processing method: '+str(cv.get('mode','Unavailable')))
    for item in (cv.get('items') or cv.get('criteria') or cv.get('evidence') or [])[:20]:
        if isinstance(item,dict):
            add(f"Requirement: {item.get('requirement') or item.get('skill') or 'Criterion'}")
            add('Evidence: '+str(item.get('excerpt') or item.get('evidence') or item.get('quote') or item.get('reason') or 'Not clearly evidenced'))
    add('Video interview — submitted answer text','SectionIL')
    for question in questions[:12]:
        add(f'{question.order}. {question.prompt}')
        add('Candidate transcript: '+(question.transcript or '[not submitted]')[:2500])
    report=application.video_review or {}
    if report:
        add('Transcript-based AI evidence (not a decision)','SectionIL')
        add('Processing method: '+str(report.get('mode','Unavailable')))
        for item in (report.get('items') or report.get('observations') or report.get('criteria') or [])[:12]:
            if isinstance(item,dict):
                add(str(item.get('skill') or item.get('requirement') or 'Observation')+': '+str(item.get('evidence') or item.get('observation') or item.get('quote') or ''))
    add('Individual interview','SectionIL')
    add('Scheduled: '+str(application.interview_datetime or 'Not yet scheduled'))
    if not candidate_view:
        add('Recruiter notes','SectionIL');add(application.recruiter_notes or 'No reviewer notes recorded')
        if application.individual_feedback:
            add('Final recorded human reasoning: '+str(application.individual_feedback.get('notes','')))
            for key,value in (application.individual_feedback.get('rubric') or {}).items():
                add(key+': '+str(value))
    add('Privacy & review notice','SectionIL')
    add('Camera-facing and eye-direction feedback is optional, approximate, on-device only and excluded from this packet. Do not interpret gaze as cheating or honesty. No automated offer or rejection is issued by this report.')
    doc.build(story)
    return buffer.getvalue()
