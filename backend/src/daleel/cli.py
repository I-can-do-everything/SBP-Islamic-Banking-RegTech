"""Command line entry point: `daleel <command>`.

Commands:
  migrate         apply database migrations
  serve           run the API (and the embedded worker) with uvicorn
  worker          run a standalone pipeline worker
  samples         (re)generate the synthetic sample workbooks
  index-sources   (re)load the SBP source excerpts used for retrieval
  cleanup         delete expired demo workspaces
"""

from __future__ import annotations

import argparse
import os
import time


def main() -> None:
    parser = argparse.ArgumentParser(prog="daleel")
    parser.add_argument("command", choices=["migrate", "serve", "worker", "samples", "index-sources", "cleanup"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args = parser.parse_args()

    if args.command == "migrate":
        from daleel.db.database import migrate
        print("applied:", migrate() or "nothing new")
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("daleel.api.app:app", host=args.host, port=args.port, proxy_headers=True)
    elif args.command == "worker":
        from daleel.pipeline import jobs  # noqa: F401
        from daleel.pipeline.queue import Worker
        worker = Worker()
        worker.start()
        while True:
            time.sleep(3600)
    elif args.command == "samples":
        from daleel.api.app import SAMPLES, sample_path
        from daleel.datagen.export import build_sample
        from daleel.datagen.generator import Scenario
        for name in SAMPLES:
            print(build_sample(Scenario(name=name), sample_path(name))["path"])
    elif args.command == "index-sources":
        from daleel.ai.sources import build_index
        print("chunks:", build_index())
    elif args.command == "cleanup":
        from daleel.pipeline.jobs import cleanup_expired
        print("deleted workspaces:", cleanup_expired())


if __name__ == "__main__":
    main()
