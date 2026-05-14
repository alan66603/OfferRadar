import re
import pdfplumber

_KEYWORD_RE = re.compile(
    r'\b(Python|Java|JavaScript|TypeScript|Go|Rust|C\+\+|C#|Ruby|Swift|Kotlin'
    r'|Machine Learning|Deep Learning|NLP|Computer Vision|LLM'
    r'|PyTorch|TensorFlow|scikit-learn|Keras|Hugging Face'
    r'|AWS|GCP|Azure|Docker|Kubernetes|Terraform|CI/CD'
    r'|React|Vue|Angular|Node\.js|FastAPI|Django|Flask|Spring'
    r'|SQL|PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch'
    r'|Git|Linux|REST|GraphQL|gRPC)\b',
    re.IGNORECASE,
)


def extract_resume(pdf_path: str) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        pages_text = [page.extract_text() or "" for page in pdf.pages]
    full_text = "\n".join(pages_text)
    matches = _KEYWORD_RE.findall(full_text)
    keywords = list({kw.title() if kw.islower() else kw for kw in matches})
    return {"text": full_text, "keywords": keywords}
