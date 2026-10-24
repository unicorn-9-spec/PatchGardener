from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Repository(StrictModel):
    id: str
    name: str
    path: str
    synthetic: bool = False
    execution: str = "Static checks only"


class IssueEvidence(StrictModel):
    tool: str
    code: str
    path: str
    line: int
    column: int = 1
    excerpt: str
    message: str


class Issue(StrictModel):
    id: str
    title: str
    severity: Literal["low", "medium"]
    evidence: IssueEvidence
    withheld: bool = False
    reason: str | None = None


class ScanRequest(StrictModel):
    repository_id: str = "demo"


class Scan(StrictModel):
    id: str
    repository: Repository
    created_at: str
    files: int
    bytes: int
    issues: list[Issue]
    snapshot: dict[str, str]
    fingerprint: str
    duration_ms: int


class Edit(StrictModel):
    path: str = Field(min_length=1, max_length=240)
    old: str = Field(min_length=1, max_length=12000)
    new: str = Field(max_length=12000)


class ModelReply(StrictModel):
    summary: str = Field(min_length=1, max_length=1000)
    edits: list[Edit] = Field(min_length=1, max_length=4)


class ProposeRequest(StrictModel):
    scan_id: str
    issue_id: str


class RiskReason(StrictModel):
    rule: str
    explanation: str


class PatchProposal(StrictModel):
    id: str
    scan_id: str
    issue_id: str
    summary: str
    model: str
    model_digest: str
    inference_ms: int
    edits: list[Edit]
    diff: str
    before: dict[str, str]
    after: dict[str, str]
    risk: Literal["low", "medium"]
    reasons: list[RiskReason]
    lines_changed: int
    status: str = "awaiting_approval"


class Approval(StrictModel):
    proposal_id: str
    approved: Literal[True]


class Check(StrictModel):
    name: str
    status: Literal["passed", "failed", "skipped"]
    output: str
    duration_ms: int


class ValidationRun(StrictModel):
    id: str
    proposal_id: str
    copy_path: str
    baseline: list[Check]
    checks: list[Check]
    before_issues: int
    after_issues: int
    resolved: int
    regressions: int
    verdict: Literal["passed", "failed"]
    source_unchanged: bool
    diff: str
    created_at: str
