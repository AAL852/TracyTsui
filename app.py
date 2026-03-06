"""
Paper Wiper - Flask Backend
Handles PDF upload, processing, and download.
"""

import os
import uuid
import threading
import time
from pathlib import Path
from flask import (Flask, request, jsonify, send_file,
                   send_from_directory, abort)
from werkzeug.utils import secure_filename

from engine import process_pdf

# ── Config ───────────────────────────────────────────────────────────────────
UPLOAD_FOLDER  = Path("uploads")
OUTPUT_FOLDER  = Path("outputs")
MAX_FILE_MB    = 50
CLEANUP_AFTER  = 3600   # delete files after 1 hour (seconds)

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_MB * 1024 * 1024

# job store: {job_id: {status, progress, total, output, preview, error}}
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


def cleanup_job(job_id: str, delay: int = CLEANUP_AFTER):
    """Delete files after delay seconds."""
    def _delete():
        time.sleep(delay)
        with jobs_lock:
            job = jobs.pop(job_id, {})
        for key in ("input", "output", "preview"):
            p = job.get(key)
            if p and Path(p).exists():
                try:
                    Path(p).unlink()
                except Exception:
                    pass
    threading.Thread(target=_delete, daemon=True).start()


def run_job(job_id: str, input_path: str):
    output_path  = str(OUTPUT_FOLDER / f"{job_id}_clean.pdf")
    preview_path = str(OUTPUT_FOLDER / f"{job_id}_preview.pdf")

    def progress(current, total):
        with jobs_lock:
            jobs[job_id]["progress"] = current
            jobs[job_id]["total"]    = total

    try:
        stats = process_pdf(
            input_path, output_path,
            preview_path=preview_path,
            dpi=200,
            progress_callback=progress,
        )
        with jobs_lock:
            jobs[job_id].update({
                "status":  "done",
                "output":  output_path,
                "preview": preview_path,
                "stats":   stats,
            })
    except Exception as exc:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"]  = str(exc)
    finally:
        cleanup_job(job_id)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename or not allowed_file(f.filename):
        return jsonify({"error": "Only PDF files are accepted"}), 400

    job_id     = str(uuid.uuid4())
    filename   = secure_filename(f.filename)
    input_path = str(UPLOAD_FOLDER / f"{job_id}_{filename}")
    f.save(input_path)

    with jobs_lock:
        jobs[job_id] = {
            "status":   "processing",
            "progress": 0,
            "total":    1,
            "input":    input_path,
            "output":   None,
            "preview":  None,
            "error":    None,
        }

    thread = threading.Thread(target=run_job, args=(job_id, input_path),
                              daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/api/status/<job_id>")
def status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status":   job["status"],
        "progress": job["progress"],
        "total":    job["total"],
        "stats":    job.get("stats"),
        "error":    job.get("error"),
    })


@app.route("/api/download/<job_id>/<file_type>")
def download(job_id: str, file_type: str):
    if file_type not in ("clean", "preview"):
        abort(400)
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job["status"] != "done":
        abort(404)

    key  = "output" if file_type == "clean" else "preview"
    path = job.get(key)
    if not path or not Path(path).exists():
        abort(404)

    dl_name = f"wiped_paper.pdf" if file_type == "clean" else "preview_marked.pdf"
    return send_file(path, as_attachment=True, download_name=dl_name,
                     mimetype="application/pdf")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
