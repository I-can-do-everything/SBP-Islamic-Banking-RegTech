"""Pipeline jobs: ingest, then calculate, then narrate.

Each job is idempotent (running it again replaces its own output) and writes
progress events that the browser receives live over Server Sent Events.
Each job enqueues the next one in the same transaction as its results, so the
pipeline can never stop half way without a record of where it stopped.
"""

from __future__ import annotations

import calendar
import json
import logging
import shutil
from datetime import date
from pathlib import Path
from uuid import UUID

from daleel.ai.narrative import generate_breakdown
from daleel.core.config import get_settings
from daleel.core.errors import DaleelError
from daleel.db.database import system_tx, workspace_tx
from daleel.ingestion.service import ingest_file
from daleel.ingestion.template import write_template
from daleel.pipeline.process import process
from daleel.pipeline.queue import enqueue, handler
from daleel.storage import store

log = logging.getLogger("daleel.jobs")


def event(conn, ws: UUID, sub: UUID, stage: str, status: str, message: str, data: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO submission_event (workspace_id, submission_id, stage, status, message, data)"
        " VALUES (%s,%s,%s,%s,%s,%s)", (ws, sub, stage, status, message, json.dumps(data or {})))


def audit(conn, ws: UUID, actor: str, action: str, resource: str, details: dict) -> None:
    conn.execute("INSERT INTO audit_event (workspace_id, actor, action, resource, details) VALUES (%s,%s,%s,%s,%s)",
                 (ws, actor, action, resource, json.dumps(details, default=str)))


def sub_dir(ws: UUID, sub: UUID) -> str:
    return f"{ws}/{sub}"


def _fail(ws: UUID, sub: UUID, stage: str, exc: Exception) -> None:
    message = exc.message if isinstance(exc, DaleelError) else f"Unexpected error: {type(exc).__name__}"
    with workspace_tx(ws) as conn:
        conn.execute("UPDATE submission SET status = 'FAILED', error = %s, updated_at = now() WHERE id = %s",
                     (json.dumps({"stage": stage, "message": message}), sub))
        event(conn, ws, sub, stage, "error", message)
        audit(conn, ws, "system", f"{stage}.failed", f"submission/{sub}", {"message": message})


@handler("ingest")
def ingest_job(ws: UUID, payload: dict) -> None:
    sub = UUID(payload["submission_id"])
    with workspace_tx(ws) as conn:
        upload = conn.execute("SELECT * FROM upload WHERE submission_id = %s", (sub,)).fetchone()
        submission = conn.execute("SELECT * FROM submission WHERE id = %s", (sub,)).fetchone()
        conn.execute("UPDATE submission SET status = 'INGESTING', stage = 'ingest', updated_at = now() WHERE id = %s",
                     (sub,))
        event(conn, ws, sub, "ingest", "running", "Reading the file and recognising its sheets")
    try:
        data = store.get_bytes(upload["storage_key"])
        if store.sha256_bytes(data) != upload["sha256"]:
            raise DaleelError("hash_mismatch", "The stored file does not match the uploaded file's fingerprint.")
        silver = store.path_for(f"{sub_dir(ws, sub)}/silver")
        if silver.exists():
            shutil.rmtree(silver)
        result = ingest_file(data, upload["filename"], silver)
        summary = result.summary()
        meta = summary["meta"]
        period_end = submission["period_end"] or (date.fromisoformat(meta["period_end"]) if meta.get("period_end") else None)
        if period_end is None:
            raise DaleelError("no_period", "The reporting date was not found in the file. Add an INFO sheet with "
                                           "'Period end', or enter the date when uploading.")
        period_days = submission["period_days"] or meta.get("period_days") or \
            calendar.monthrange(period_end.year, period_end.month)[1]
        institution = meta.get("institution") or submission["institution"]
        template_key = f"{sub_dir(ws, sub)}/reports/Daleel_Standard_Template.xlsx"
        template_path = store.path_for(template_key)
        template_path.parent.mkdir(parents=True, exist_ok=True)
        write_template(template_path, summary, {k: d.parquet_path for k, d in result.datasets.items()},
                       {"filename": upload["filename"], "sha256": upload["sha256"]})
    except Exception as exc:
        log.exception("ingest failed")
        _fail(ws, sub, "ingest", exc)
        return
    with workspace_tx(ws) as conn:
        conn.execute("DELETE FROM dataset WHERE submission_id = %s", (sub,))
        for kind, d in result.datasets.items():
            path = Path(d.parquet_path)
            conn.execute(
                "INSERT INTO dataset (workspace_id, submission_id, kind, source_name, layout, row_count,"
                " rejected_count, canonical_key, canonical_sha256, header_map, fixes, preview)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (ws, sub, kind, d.source_name, d.layout, d.row_count, d.rejected_count,
                 f"{sub_dir(ws, sub)}/silver/{path.name}", store.sha256_file(path),
                 json.dumps(d.header_map), json.dumps({"fixes": d.fixes, "translations": d.translations,
                                                       "structural": d.structural}),
                 json.dumps({"before": d.preview_before, "after": d.preview_after})))
        summary["template_key"] = template_key
        conn.execute(
            "UPDATE submission SET status = 'INGESTED', stage = 'ingest', institution = %s, period_end = %s,"
            " period_days = %s, ingestion = %s, updated_at = now() WHERE id = %s",
            (institution, period_end, period_days, json.dumps(summary, default=str), sub))
        total_fixes = sum(f["cells"] for d in result.datasets.values() for f in d.fixes)
        event(conn, ws, sub, "ingest", "done",
              f"Recognised {len(result.datasets)} datasets and transformed them into the standard template",
              {"datasets": {k: d.row_count for k, d in result.datasets.items()}, "fixes": total_fixes,
               "rejected": sum(d.rejected_count for d in result.datasets.values())})
        audit(conn, ws, "system", "ingest.completed", f"submission/{sub}",
              {"datasets": list(result.datasets), "template_version": summary["template_version"]})
        enqueue(conn, "calculate", ws, {"submission_id": str(sub)})


def _metrics_payload(conn, sub: UUID) -> tuple[list[dict], list[dict]]:
    metrics = [{"id": r["metric_id"], "category": r["category"], "label": r["label"], "unit": r["unit"],
                "value": None if r["value"] is None else str(r["value"]), "status": r["status"], "detail": r["detail"]}
               for r in conn.execute("SELECT * FROM metric_result WHERE submission_id = %s ORDER BY sort_order",
                                     (sub,))]
    checks = [{"id": r["check_id"], "category": r["category"], "label": r["label"], "status": r["status"],
               "message": r["message"], "evidence": r["evidence"], "rule_refs": r["rule_refs"]}
              for r in conn.execute("SELECT * FROM validation_result WHERE submission_id = %s ORDER BY sort_order",
                                    (sub,))]
    return metrics, checks


@handler("calculate")
def calculate_job(ws: UUID, payload: dict) -> None:
    sub = UUID(payload["submission_id"])
    with workspace_tx(ws) as conn:
        submission = conn.execute("SELECT * FROM submission WHERE id = %s", (sub,)).fetchone()
        datasets = conn.execute("SELECT kind, canonical_key FROM dataset WHERE submission_id = %s", (sub,)).fetchall()
        conn.execute("UPDATE submission SET status = 'PROCESSING', stage = 'calculate', updated_at = now()"
                     " WHERE id = %s", (sub,))
        event(conn, ws, sub, "calculate", "running", "Mapping accounts, classifying financing and computing ratios")
    try:
        parquet = {d["kind"]: str(store.path_for(d["canonical_key"])) for d in datasets}
        result = process(parquet, submission["period_end"], submission["period_days"], submission["ingestion"])
    except Exception as exc:
        log.exception("calculate failed")
        _fail(ws, sub, "calculate", exc)
        return
    with workspace_tx(ws) as conn:
        for table in ("metric_result", "validation_result", "gold_balance"):
            conn.execute(f"DELETE FROM {table} WHERE submission_id = %s", (sub,))
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO metric_result (workspace_id, submission_id, metric_id, category, label, unit, value,"
                " status, detail, sort_order) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [(ws, sub, m.id, m.category, m.label, m.unit, m.value, m.status,
                  json.dumps(m.detail(), default=str), m.sort_order) for m in result.metrics])
            cur.executemany(
                "INSERT INTO validation_result (workspace_id, submission_id, check_id, category, label, status,"
                " message, evidence, rule_refs, sort_order) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                [(ws, sub, c.id, c.category, c.label, c.status, c.message, json.dumps(c.evidence, default=str),
                  json.dumps(c.rule_refs, default=str), i) for i, c in enumerate(result.checks)])
            cur.executemany(
                "INSERT INTO gold_balance (workspace_id, submission_id, code, label, normal_side, signed_amount,"
                " presented, source_count) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                [(ws, sub, g["code"], g["label"], g["normal"], g["signed_amount"], g["presented"], g["source_count"])
                 for g in result.gold])
        mapping = {"version": result.mapping_version,
                   "unmapped": result.mapping.unmapped if result.mapping else [],
                   "overlaps": result.mapping.overlaps if result.mapping else [],
                   "abnormal": result.mapping.abnormal if result.mapping else []}
        conn.execute("UPDATE submission SET ingestion = jsonb_set(ingestion, '{mapping}', %s) WHERE id = %s",
                     (json.dumps(mapping), sub))
        counts = {s: sum(1 for m in result.metrics if m.status == s) + sum(1 for c in result.checks if c.status == s)
                  for s in ("PASS", "WARNING", "FAIL")}
        conn.execute("UPDATE submission SET status = 'READY', stage = 'narrate', updated_at = now() WHERE id = %s",
                     (sub,))
        event(conn, ws, sub, "calculate", "done", "Calculated every metric and check", counts)
        audit(conn, ws, "system", "calculate.completed", f"submission/{sub}",
              {"metrics": len(result.metrics), "checks": len(result.checks), "counts": counts,
               "mapping_version": result.mapping_version})
        metrics, checks = _metrics_payload(conn, sub)
        _store_breakdown(conn, ws, sub, generate_breakdown(metrics, checks, use_ai=False))
        enqueue(conn, "narrate", ws, {"submission_id": str(sub)})


def _store_breakdown(conn, ws: UUID, sub: UUID, breakdown) -> None:
    out = breakdown.as_dict()
    conn.execute(
        "INSERT INTO ai_narrative (workspace_id, submission_id, source, provider, model, prompt_version,"
        " input_sha256, output, grounding, usage) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (ws, sub, breakdown.source, breakdown.provider, breakdown.model, breakdown.prompt_version,
         breakdown.input_sha256, json.dumps({k: out[k] for k in ("headline", "points", "facts", "excerpts")},
                                            default=str),
         json.dumps(breakdown.grounding, default=str), json.dumps(breakdown.usage, default=str)))


@handler("narrate")
def narrate_job(ws: UUID, payload: dict) -> None:
    sub = UUID(payload["submission_id"])
    with workspace_tx(ws) as conn:
        metrics, checks = _metrics_payload(conn, sub)
        event(conn, ws, sub, "narrate", "running", "Writing the AI breakdown (grounded on the verified results)")
    breakdown = generate_breakdown(metrics, checks)
    with workspace_tx(ws) as conn:
        _store_breakdown(conn, ws, sub, breakdown)
        conn.execute("UPDATE submission SET stage = 'done', updated_at = now() WHERE id = %s", (sub,))
        message = ("AI breakdown written and verified against the results" if breakdown.source == "ai" else
                   "AI was unavailable; a deterministic summary was written instead")
        event(conn, ws, sub, "narrate", "done", message, {"source": breakdown.source, "model": breakdown.model})
        audit(conn, ws, "system", "narrate.completed", f"submission/{sub}",
              {"source": breakdown.source, "model": breakdown.model, "input_sha256": breakdown.input_sha256,
               "grounding": breakdown.grounding.get("status")})


def cleanup_expired() -> int:
    """Delete expired demo workspaces and their files."""
    with system_tx() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM workspace_registry WHERE expires_at < now()")]
    for ws in ids:
        with workspace_tx(ws) as conn:
            conn.execute("DELETE FROM workspace WHERE id = %s", (ws,))
        with system_tx() as conn:
            conn.execute("DELETE FROM workspace_registry WHERE id = %s", (ws,))
            conn.execute("DELETE FROM job WHERE workspace_id = %s", (ws,))
        path = get_settings().data_dir / "store" / str(ws)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    return len(ids)

