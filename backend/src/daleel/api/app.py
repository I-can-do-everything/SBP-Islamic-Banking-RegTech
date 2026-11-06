"""HTTP API for the Daleel demo (FastAPI).

All endpoints live under /api/v1. Errors use RFC 9457 problem details.
Amounts are strings in JSON, so no precision is lost on the way to the browser.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from daleel import __version__
from daleel.api.security import (
    WorkspaceDep,
    create_workspace,
    session_limit,
    token_from_query,
    upload_limit,
)
from daleel.core.config import get_settings
from daleel.core.errors import DaleelError, InvalidInput, NotFound
from daleel.db.database import migrate, system_tx, workspace_tx
from daleel.pipeline import jobs
from daleel.pipeline.queue import Worker, enqueue
from daleel.rulebook.rulebook import load_rulebook
from daleel.storage import store

log = logging.getLogger("daleel.api")

SAMPLES = {
    "baseline": {"title": "Example Islamic Bank: September 2026 (healthy)",
                 "description": "A messy T24 and Flexcube style export of a healthy bank. Expect clean "
                                "transformations, one unmapped account and passing ratios."},
    "stressed": {"title": "Example Islamic Bank: September 2026 (stressed)",
                 "description": "The same bank under stress, with planted breaches: a savings tier below 75% of "
                                "the pool yield, Mudarib share above 50%, late weightage notice, charity booked as "
                                "income, a provision shortfall and an unreadable cell."},
}


def sample_path(name: str) -> Path:
    return get_settings().data_dir / "samples" / f"EXIB_regulatory_extract_2026-09_{name}.xlsx"


def ensure_samples() -> None:
    from daleel.datagen.export import build_sample
    from daleel.datagen.generator import Scenario

    for name in SAMPLES:
        path = sample_path(name)
        if not path.exists():
            build_sample(Scenario(name=name), path)


def ensure_sources() -> None:
    from daleel.ai.sources import build_index

    with system_tx() as conn:
        count = conn.execute("SELECT count(*) AS n FROM source_chunk").fetchone()["n"]
    if count == 0:
        build_index()


worker = Worker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    migrate()
    ensure_sources()
    ensure_samples()
    if get_settings().embedded_worker:
        worker.start()
    yield
    worker.stop()


app = FastAPI(title="Daleel API", version=__version__, lifespan=lifespan,
              description="Daleel: an Islamic bank regulatory compliance tool. Demo API on synthetic data.")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origin_list, allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=False)


@app.exception_handler(DaleelError)
async def daleel_error(request: Request, exc: DaleelError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, media_type="application/problem+json",
                        content={"type": f"https://daleel.dev/errors/{exc.code}", "title": exc.message,
                                 "status": exc.status, "code": exc.code, **exc.details})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# --------------------------------------------------------------------- health and session

@app.get("/health")
def health() -> dict:
    with system_tx() as conn:
        conn.execute("SELECT 1")
    s = get_settings()
    return {"status": "ok", "version": __version__, "ai_provider": s.ai_provider,
            "ai_configured": s.ai_provider == "ollama" or bool(s.openrouter_api_key)}


@app.post("/api/v1/session", dependencies=[Depends(session_limit)])
def start_session() -> dict:
    ws, token, expires = create_workspace()
    return {"token": token, "workspace_id": str(ws), "expires_at": expires.isoformat()}


# --------------------------------------------------------------------- samples

@app.get("/api/v1/samples")
def samples() -> list[dict]:
    return [{"name": k, **v, "filename": sample_path(k).name} for k, v in SAMPLES.items()]


@app.get("/api/v1/samples/{name}/download")
def download_sample(name: str) -> FileResponse:
    if name not in SAMPLES:
        raise NotFound("no_sample", "Unknown sample.")
    return FileResponse(sample_path(name), filename=sample_path(name).name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# --------------------------------------------------------------------- submissions

def _create_submission(ws: UUID, filename: str, data: bytes, period_end: str | None) -> dict:
    settings = get_settings()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise InvalidInput("too_large", f"Files up to {settings.max_upload_mb} MB are accepted in the demo.")
    if not data:
        raise InvalidInput("empty", "The file is empty.")
    safe_name = Path(filename).name[:120] or "upload"
    with workspace_tx(ws) as conn:
        sub = conn.execute(
            "INSERT INTO submission (workspace_id, institution, period_end) VALUES (%s, %s, %s) RETURNING id",
            (ws, "Unknown institution", period_end or None)).fetchone()["id"]
        key = f"{ws}/{sub}/raw/{safe_name}"
        sha = store.put_bytes(key, data, immutable=True)
        conn.execute("INSERT INTO upload (workspace_id, submission_id, filename, sha256, size_bytes, storage_key)"
                     " VALUES (%s,%s,%s,%s,%s,%s)", (ws, sub, safe_name, sha, len(data), key))
        jobs.event(conn, ws, sub, "upload", "done", f"Received {safe_name}", {"sha256": sha, "bytes": len(data)})
        jobs.audit(conn, ws, "visitor", "upload.received", f"submission/{sub}",
                   {"filename": safe_name, "sha256": sha, "bytes": len(data)})
        enqueue(conn, "ingest", ws, {"submission_id": str(sub)})
    return {"id": str(sub), "sha256": sha, "filename": safe_name}


@app.post("/api/v1/submissions", dependencies=[Depends(upload_limit)])
async def create_submission(file: UploadFile | None = File(default=None), sample: str | None = Form(default=None),
                            period_end: str | None = Form(default=None), ws: UUID = WorkspaceDep) -> dict:
    if sample:
        if sample not in SAMPLES:
            raise InvalidInput("no_sample", "Unknown sample.")
        path = sample_path(sample)
        return _create_submission(ws, path.name, path.read_bytes(), period_end)
    if file is None:
        raise InvalidInput("no_file", "Choose a file or a sample.")
    data = await file.read(get_settings().max_upload_mb * 1024 * 1024 + 1)
    return _create_submission(ws, file.filename or "upload", data, period_end)


def _submission(conn, sub: UUID) -> dict:
    row = conn.execute("SELECT s.*, u.filename, u.sha256, u.size_bytes FROM submission s"
                       " LEFT JOIN upload u ON u.submission_id = s.id WHERE s.id = %s", (sub,)).fetchone()
    if row is None:
        raise NotFound("no_submission", "Submission not found.")
    return row


def _sub_json(row: dict) -> dict:
    return {"id": str(row["id"]), "institution": row["institution"],
            "period_end": row["period_end"].isoformat() if row["period_end"] else None,
            "period_days": row["period_days"], "status": row["status"], "stage": row["stage"],
            "error": row["error"], "filename": row.get("filename"), "sha256": row.get("sha256"),
            "size_bytes": row.get("size_bytes"), "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat()}


@app.get("/api/v1/submissions")
def list_submissions(ws: UUID = WorkspaceDep) -> list[dict]:
    with workspace_tx(ws) as conn:
        rows = conn.execute("SELECT s.*, u.filename, u.sha256, u.size_bytes FROM submission s"
                            " LEFT JOIN upload u ON u.submission_id = s.id ORDER BY s.created_at DESC").fetchall()
    return [_sub_json(r) for r in rows]


@app.get("/api/v1/submissions/{sub}")
def get_submission(sub: UUID, ws: UUID = WorkspaceDep) -> dict:
    with workspace_tx(ws) as conn:
        return _sub_json(_submission(conn, sub))


@app.get("/api/v1/submissions/{sub}/events")
def submission_events(sub: UUID, ws: UUID = Depends(token_from_query)) -> StreamingResponse:
    """Server Sent Events: replays past events, then streams new ones until the pipeline finishes."""

    def stream():
        last_id, idle = 0, 0
        while idle < 1200:  # about 10 minutes at most
            with workspace_tx(ws) as conn:
                rows = conn.execute("SELECT id, at, stage, status, message, data FROM submission_event"
                                    " WHERE submission_id = %s AND id > %s ORDER BY id", (sub, last_id)).fetchall()
                state = conn.execute("SELECT status, stage FROM submission WHERE id = %s", (sub,)).fetchone()
            for r in rows:
                last_id = r["id"]
                payload = {"id": r["id"], "at": r["at"].isoformat(), "stage": r["stage"], "status": r["status"],
                           "message": r["message"], "data": r["data"]}
                yield f"id: {r['id']}\nevent: progress\ndata: {json.dumps(payload)}\n\n"
            if state is None or state["status"] == "FAILED" or state["stage"] == "done":
                yield "event: end\ndata: {}\n\n"
                return
            idle += 1
            if idle % 30 == 0:
                yield ": keep-alive\n\n"
            time.sleep(0.5)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/submissions/{sub}/ingestion")
def get_ingestion(sub: UUID, ws: UUID = WorkspaceDep) -> dict:
    with workspace_tx(ws) as conn:
        row = _submission(conn, sub)
        datasets = conn.execute("SELECT kind, source_name, layout, row_count, rejected_count, canonical_sha256,"
                                " header_map, fixes, preview FROM dataset WHERE submission_id = %s ORDER BY kind",
                                (sub,)).fetchall()
    summary = row["ingestion"] or {}
    return {"submission": _sub_json(row), "template_version": summary.get("template_version"),
            "meta": summary.get("meta"), "skipped_sheets": summary.get("skipped_sheets", []),
            "missing_datasets": summary.get("missing_datasets", []), "mapping": summary.get("mapping"),
            "datasets": [{**{k: v for k, v in d.items() if k not in ("fixes", "preview")},
                          **d["fixes"], **d["preview"],
                          "detail": (summary.get("datasets") or {}).get(d["kind"], {}).get("layout_evidence"),
                          "ignored_columns": (summary.get("datasets") or {}).get(d["kind"], {}).get("ignored_columns"),
                          "rejects_sample": (summary.get("datasets") or {}).get(d["kind"], {}).get("rejects_sample")}
                         for d in datasets]}


@app.get("/api/v1/submissions/{sub}/results")
def get_results(sub: UUID, ws: UUID = WorkspaceDep) -> dict:
    with workspace_tx(ws) as conn:
        row = _submission(conn, sub)
        metrics = conn.execute("SELECT metric_id, category, label, unit, value, status, detail FROM metric_result"
                               " WHERE submission_id = %s ORDER BY sort_order", (sub,)).fetchall()
        checks = conn.execute("SELECT check_id, category, label, status, message, evidence, rule_refs"
                              " FROM validation_result WHERE submission_id = %s ORDER BY sort_order", (sub,)).fetchall()
        gold = conn.execute("SELECT code, label, normal_side, signed_amount, presented, source_count FROM gold_balance"
                            " WHERE submission_id = %s ORDER BY code", (sub,)).fetchall()
    return {
        "submission": _sub_json(row),
        "metrics": [{"id": m["metric_id"], "category": m["category"], "label": m["label"], "unit": m["unit"],
                     "value": None if m["value"] is None else str(m["value"]), "status": m["status"],
                     **m["detail"]} for m in metrics],
        "checks": [{"id": c["check_id"], "category": c["category"], "label": c["label"], "status": c["status"],
                    "message": c["message"], "evidence": c["evidence"], "rules": c["rule_refs"]} for c in checks],
        "gold": [{"code": g["code"], "label": g["label"], "normal_side": g["normal_side"],
                  "signed_amount": str(g["signed_amount"]), "presented": str(g["presented"]),
                  "source_count": g["source_count"]} for g in gold],
        "mapping": (row["ingestion"] or {}).get("mapping"),
    }


@app.get("/api/v1/submissions/{sub}/breakdown")
def get_breakdown(sub: UUID, ws: UUID = WorkspaceDep) -> dict:
    with workspace_tx(ws) as conn:
        _submission(conn, sub)
        row = conn.execute("SELECT * FROM ai_narrative WHERE submission_id = %s ORDER BY created_at DESC LIMIT 1",
                           (sub,)).fetchone()
    if row is None:
        return {"status": "pending"}
    return {"status": "ready", "source": row["source"], "provider": row["provider"], "model": row["model"],
            "prompt_version": row["prompt_version"], "input_sha256": row["input_sha256"],
            "created_at": row["created_at"].isoformat(), **row["output"], "grounding": row["grounding"]}


@app.get("/api/v1/submissions/{sub}/template.xlsx")
def download_template(sub: UUID, ws: UUID = Depends(token_from_query)) -> FileResponse:
    with workspace_tx(ws) as conn:
        row = _submission(conn, sub)
    key = (row["ingestion"] or {}).get("template_key")
    if not key or not store.exists(key):
        raise NotFound("no_template", "The standard template has not been generated yet.")
    period = row["period_end"].isoformat() if row["period_end"] else "period"
    return FileResponse(store.path_for(key), filename=f"Daleel_Standard_Template_{period}.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# --------------------------------------------------------------------- reference data

@app.get("/api/v1/rulebook")
def rulebook(as_of: str | None = None) -> list[dict]:
    from datetime import date

    day = date.fromisoformat(as_of) if as_of else date.today()
    out = []
    for r in load_rulebook().all_in_force(day):
        ref = r.ref()
        ref["table"] = {k: (str(v) if not isinstance(v, list) else v) for k, v in (r.table or {}).items()} or None
        ref["list"] = list(r.items) if r.items else None
        ref["notes"] = r.notes
        out.append(ref)
    return out


@app.get("/api/v1/sources/{chunk_id}")
def source_excerpt(chunk_id: str) -> dict:
    with system_tx() as conn:
        row = conn.execute("SELECT id, doc_id, doc_title, url, section, page, verification, text FROM source_chunk"
                           " WHERE id = %s", (chunk_id,)).fetchone()
    if row is None:
        raise NotFound("no_source", "Source excerpt not found.")
    return dict(row)


# --------------------------------------------------------------------- audit

@app.get("/api/v1/audit")
def audit_log(ws: UUID = WorkspaceDep) -> list[dict]:
    with workspace_tx(ws) as conn:
        rows = conn.execute("SELECT id, occurred_at, actor, action, resource, details, prev_hash, hash"
                            " FROM audit_event ORDER BY id").fetchall()
    return [{**r, "occurred_at": r["occurred_at"].isoformat()} for r in rows]


@app.get("/api/v1/audit/verify")
def audit_verify(ws: UUID = WorkspaceDep) -> dict:
    """Recompute every hash in this workspace's chain and report the first break, if any."""
    with workspace_tx(ws) as conn:
        rows = conn.execute("""
            SELECT id, hash, prev_hash,
                   encode(sha256(convert_to(coalesce(prev_hash, 'GENESIS') || '|' || workspace_id::text || '|' ||
                     to_char(occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || '|' ||
                     actor || '|' || action || '|' || coalesce(resource, '') || '|' || details::text,
                     'UTF8')), 'hex') AS recomputed
            FROM audit_event ORDER BY id""").fetchall()
    previous = None
    for r in rows:
        if r["recomputed"] != r["hash"] or r["prev_hash"] != previous:
            return {"valid": False, "events": len(rows), "broken_at": r["id"]}
        previous = r["hash"]
    return {"valid": True, "events": len(rows), "head": previous}


# --------------------------------------------------------------------- web app (single container deploys)

_dist = get_settings().web_dist
if (_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Serve the React app; unknown paths return index.html so client side routes work."""
        candidate = (_dist / path).resolve()
        if path and _dist.resolve() in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
