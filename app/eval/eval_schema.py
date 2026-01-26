from pydantic import BaseModel
from typing import List

class EvaluationCheck(BaseModel):
    check_name: str
    justification: str
    check_pass: bool

class EvaluationChecklist(BaseModel):
    checklist: List[EvaluationCheck]
    summary: str