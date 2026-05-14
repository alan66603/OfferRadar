from offerradar.parsers import parse_email


LINKEDIN_HTML = """
<html><body>
<table>
  <tr>
    <td>
      <a href="https://www.linkedin.com/comm/jobs/view/111111/?trackingId=abc">ML Engineer Intern</a><br>
      Qualcomm · Hsinchu City
    </td>
  </tr>
  <tr>
    <td>
      <a href="https://www.linkedin.com/comm/jobs/view/222222/?trackingId=def">Data Analyst Intern</a><br>
      Micron Technology · Zhubei City
    </td>
  </tr>
</table>
</body></html>
"""

GLASSDOOR_HTML = """
<html><body>
<a href="https://www.glassdoor.com/partner/jobListing.htm?jobListingId=123456&src=GD_JOB_AD" style="text-decoration:none">
  <table><tbody><tr><td>
    <span style="font-size:12px;font-weight:400">TSMC</span>
  </td></tr></tbody></table>
  <table><tbody><tr><td>
    <p style="font-size:14px;line-height:1.4;margin:0;font-weight:600">Backend Engineer</p>
  </td></tr></tbody></table>
</a>
</body></html>
"""

INDEED_HTML = """
<html><body>
<table>
  <tr>
    <td><a href="https://tw.indeed.com/viewjob?jk=abc123">Software Engineer</a></td>
    <td>MediaTek</td>
    <td>Hsinchu</td>
  </tr>
</table>
</body></html>
"""


def test_parse_linkedin_email_returns_jobs():
    jobs = parse_email("jobs-noreply@linkedin.com", LINKEDIN_HTML)
    assert len(jobs) == 2
    assert jobs[0].title == "ML Engineer Intern"
    assert jobs[0].company == "Qualcomm"
    assert jobs[0].location == "Hsinchu City"
    assert jobs[0].url == "https://www.linkedin.com/jobs/view/111111/"
    assert jobs[0].source == "linkedin"
    assert len(jobs[0].id) == 16


def test_parse_glassdoor_email_returns_jobs():
    jobs = parse_email("noreply@glassdoor.com", GLASSDOOR_HTML)
    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].company == "TSMC"
    assert jobs[0].url == "https://www.glassdoor.com/job-listing/j?jl=123456"
    assert jobs[0].source == "glassdoor"


def test_parse_indeed_email_returns_jobs():
    jobs = parse_email("noreply@indeed.com", INDEED_HTML)
    assert len(jobs) >= 1
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].source == "indeed"


def test_parse_unknown_sender_returns_empty():
    jobs = parse_email("random@unknown.com", "<html>whatever</html>")
    assert jobs == []
