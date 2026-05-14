from unittest.mock import patch, MagicMock
from offerradar.resume_parser import extract_resume


def _mock_pdf(text: str):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = text
    mock_pdf = MagicMock()
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    mock_pdf.pages = [mock_page]
    return mock_pdf


def test_extract_resume_returns_text_and_keywords():
    fake_text = "Skills: Python, Machine Learning, PyTorch, AWS, Docker"
    with patch("offerradar.resume_parser.pdfplumber.open", return_value=_mock_pdf(fake_text)):
        result = extract_resume("resume.pdf")
    assert result["text"] == fake_text
    assert "Python" in result["keywords"]
    assert "PyTorch" in result["keywords"]
    assert "AWS" in result["keywords"]


def test_extract_resume_deduplicates_keywords():
    fake_text = "Python developer. Python experience required."
    with patch("offerradar.resume_parser.pdfplumber.open", return_value=_mock_pdf(fake_text)):
        result = extract_resume("resume.pdf")
    assert result["keywords"].count("Python") == 1
