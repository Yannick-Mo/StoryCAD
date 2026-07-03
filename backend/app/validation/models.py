from pydantic import BaseModel


class ValidationIssue(BaseModel):
    category: str
    severity: str  # critical | warning | suggestion
    element: str
    description: str
    suggestion: str = ""


class ConsistencyCheck(BaseModel):
    check_name: str
    passed: bool
    details: str = ""


class ValidationResult(BaseModel):
    overall_score: float = 0.0
    issues: list[ValidationIssue] = []
    consistency_checks: list[ConsistencyCheck] = []
    missing_elements: list[str] = []
    recommendations: list[str] = []
