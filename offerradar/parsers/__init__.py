from offerradar.models import JobPost
from offerradar.parsers.linkedin import parse_linkedin_email
from offerradar.parsers.glassdoor import parse_glassdoor_email
from offerradar.parsers.indeed import parse_indeed_email


def parse_email(sender: str, html: str) -> list[JobPost]:
    if "linkedin.com" in sender:
        return parse_linkedin_email(html)
    if "glassdoor.com" in sender:
        return parse_glassdoor_email(html)
    if "indeed.com" in sender:
        return parse_indeed_email(html)
    return []
