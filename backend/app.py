import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import engine, seed
from .model import LocalModel
from .schemas import Approval, PatchProposal, ProposeRequest, Repository, Scan, ScanRequest, ValidationRun
from .storage import Store, now, uid

PROJECT = Path(__file__).resolve().parents[1]


def create_app(data_dir: Path | None = None) -> FastAPI:
    data = (data_dir or Path(os.getenv("PG_DATA_DIR", str(PROJECT / "data")))).resolve()
    store = Store(data)
    demo_root = data / "repositories" / "meadow-notes"
    if not demo_root.exists():
        engine.materialize(demo_root, seed.FILES)
    repos = {"demo": Repository(id="demo", name="meadow-notes", path=str(demo_root), synthetic=True, execution="Hash-verified built-in tests + static checks")}
    for number, path in enumerate(filter(None, os.getenv("PG_REPO_ROOTS", "").split(os.pathsep))):
        root = Path(path).expanduser()
        if not root.is_dir() or engine.linked(root):
            raise ValueError(f"Configured repository root must be an existing real directory: {root}")
        root = root.resolve()
        if root == data or data.is_relative_to(root) or root.is_relative_to(data):
            raise ValueError("Configured repository roots must not overlap application data")
        key = f"local-{number}"
        repos[key] = Repository(id=key, name=root.name, path=str(root))
    model = LocalModel(os.getenv("PG_OLLAMA_URL", "http://127.0.0.1:11434"), os.getenv("PG_MODEL", "qwen3:8b"))
    lock = threading.Lock()
    app = FastAPI(title="PatchGardener", version="0.1.0")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "[::1]"])
    app.state.store, app.state.repos = store, repos

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in {"http://127.0.0.1:3105", "http://localhost:3105"}:
            return PlainTextResponse("Cross-origin requests are disabled", status_code=403)
        try:
            size = int(request.headers.get("content-length", "0"))
        except ValueError:
            return PlainTextResponse("Invalid Content-Length", status_code=400)
        if size > 16000:
            return PlainTextResponse("Request too large", status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(ValueError)
    async def invalid(_request: Request, error: ValueError):
        return PlainTextResponse(str(error), status_code=400)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "model": model.status(), "policy": "Local only. Explicit approval. Isolated copies. No pushes."}

    @app.get("/api/repositories", response_model=list[Repository])
    def repositories():
        return list(repos.values())

    @app.post("/api/scans", response_model=Scan)
    def scan(body: ScanRequest):
        if body.repository_id not in repos:
            raise ValueError("Select a configured repository")
        start = time.monotonic()
        repo = repos[body.repository_id]
        snapshot = engine.index(Path(repo.path))
        # Scan copied bytes: evidence and model context must correspond exactly.
        scan_id = uid()
        root = data / "snapshots" / scan_id
        engine.materialize(root, snapshot)
        issues, _ = engine.scan_files(root, snapshot)
        record = Scan(id=scan_id, repository=repo, created_at=now(), files=len(snapshot), bytes=sum(len(text.encode()) for text in snapshot.values()), issues=issues, snapshot=snapshot, fingerprint=engine.fingerprint(snapshot), duration_ms=int((time.monotonic() - start) * 1000))
        store.put("scan", record.model_dump())
        store.audit("scan.completed", {"scan_id": record.id, "files": record.files, "issues": len(issues)})
        return record

    @app.post("/api/proposals", response_model=PatchProposal)
    def propose(body: ProposeRequest):
        record = Scan.model_validate(store.get("scan", body.scan_id))
        issue = next((item for item in record.issues if item.id == body.issue_id), None)
        if issue is None:
            raise ValueError("Issue does not belong to this scan")
        if issue.withheld:
            store.audit("proposal.withheld", {"issue_id": issue.id, "reason": issue.reason})
            raise ValueError(issue.reason)
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "Another proposal or validation is running")
        try:
            reply, duration, digest = model.propose(issue, record.snapshot)
            after, diff, lines, reasons = engine.patch_gate(record.snapshot, issue, reply)
            path = issue.evidence.path
            proposal = PatchProposal(id=uid(), scan_id=record.id, issue_id=issue.id, summary=reply.summary, model=model.model, model_digest=digest, inference_ms=duration, edits=reply.edits, diff=diff, before={path: record.snapshot[path]}, after={path: after[path]}, risk="medium" if path.endswith(".py") else "low", reasons=reasons, lines_changed=lines)
            store.put("proposal", proposal.model_dump())
            store.audit("proposal.created", {"proposal_id": proposal.id, "model": model.model, "digest": digest, "inference_ms": duration})
            return proposal
        except ValueError as error:
            store.audit("proposal.rejected", {"issue_id": issue.id, "reason": str(error)})
            raise
        finally:
            lock.release()

    @app.get("/api/proposals/{proposal_id}", response_model=PatchProposal)
    def get_proposal(proposal_id: str):
        return store.get("proposal", proposal_id)

    @app.post("/api/approvals", response_model=ValidationRun)
    def approve(body: Approval):
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "Another proposal or validation is running")
        try:
            proposal = PatchProposal.model_validate(store.get("proposal", body.proposal_id))
            if proposal.status != "awaiting_approval":
                raise ValueError("This proposal has already been approved")
            record = Scan.model_validate(store.get("scan", proposal.scan_id))
            repo = repos.get(record.repository.id)
            if repo is None or repo.path != record.repository.path:
                raise ValueError("Repository configuration changed; rescan")
            root = Path(repo.path)
            if engine.fingerprint(engine.index(root)) != record.fingerprint:
                raise ValueError("Repository changed since scan; rescan before approval")
            issue = next(item for item in record.issues if item.id == proposal.issue_id)
            from .schemas import ModelReply
            after, diff, _, _ = engine.patch_gate(record.snapshot, issue, ModelReply(summary=proposal.summary, edits=proposal.edits))
            if diff != proposal.diff:
                raise ValueError("Proposal integrity check failed")
            proposal.status = "validating"
            store.put("proposal", proposal.model_dump())
            store.audit("approval.recorded", {"proposal_id": proposal.id, "approved": True})
            run_id = uid()
            base = data / "runs" / run_id / "baseline"
            copy = data / "runs" / run_id / "patched"
            engine.materialize(base, record.snapshot)
            engine.materialize(copy, after)
            patch = copy.parent / "change.patch"
            patch.write_bytes(diff.encode("utf-8"))
            # Trust is granted only for the exact built-in fixture bytes. The gate
            # proves Python executable structure is unchanged except one import.
            trusted = repo.synthetic and engine.trusted_fixture(record.snapshot)
            before_issues, baseline = engine.scan_files(base, record.snapshot)
            after_issues, checks = engine.scan_files(copy, after)
            applicability = engine.diff_applicability(base, patch)
            checks.append(applicability)
            baseline.append(engine.fixture_tests(base, trusted))
            checks.append(engine.fixture_tests(copy, trusted))
            before_sig, after_sig = engine.signatures(before_issues), engine.signatures(after_issues)
            resolved, regressions = len(before_sig - after_sig), len(after_sig - before_sig)
            unchanged = engine.fingerprint(engine.index(root)) == record.fingerprint
            test_ok = checks[-1].status != "failed"
            target_resolved = engine.signatures([issue]).isdisjoint(after_sig)
            verdict = "passed" if resolved > 0 and target_resolved and regressions == 0 and unchanged and test_ok and applicability.status == "passed" else "failed"
            run = ValidationRun(id=run_id, proposal_id=proposal.id, copy_path=str(copy), baseline=baseline, checks=checks, before_issues=len(before_issues), after_issues=len(after_issues), resolved=resolved, regressions=regressions, verdict=verdict, source_unchanged=unchanged, diff=diff, created_at=now())
            proposal.status = "validated" if verdict == "passed" else "validation_failed"
            store.put("proposal", proposal.model_dump())
            store.put("run", run.model_dump())
            store.audit("validation.completed", {"run_id": run.id, "verdict": verdict, "resolved": resolved, "regressions": regressions, "source_unchanged": unchanged})
            return run
        finally:
            lock.release()

    @app.get("/api/exports/{proposal_id}")
    def export(proposal_id: str):
        proposal = PatchProposal.model_validate(store.get("proposal", proposal_id))
        return PlainTextResponse(proposal.diff, media_type="text/x-diff", headers={"Content-Disposition": f'attachment; filename="patchgardener-{proposal.id}.patch"'})

    @app.get("/api/audit")
    def audit():
        return store.events()

    return app


app = create_app()
