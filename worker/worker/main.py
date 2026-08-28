"""Valora reliable job worker entrypoint."""
from __future__ import annotations

import logging
import signal
import threading

from app.db import SessionLocal

from worker.config import get_worker_settings
from worker.handlers import build_handler_registry
from worker.runtime import ReliableJobWorker

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_worker_settings()
    logging.basicConfig(
        level=getattr(logging, settings.valora_log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    stop = threading.Event()

    def _request_stop(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    consumer = ReliableJobWorker(
        session_factory=SessionLocal,
        handlers=build_handler_registry(session_factory=SessionLocal),
        worker_id=settings.worker_id,
        lease_duration_seconds=settings.worker_lease_duration_seconds,
        heartbeat_interval_seconds=settings.worker_heartbeat_interval_seconds,
        retry_base_seconds=settings.worker_retry_base_seconds,
    )
    logger.info(
        "Valora reliable worker started: worker_id=%s env=%s",
        settings.worker_id,
        settings.valora_env,
    )
    while not stop.is_set():
        try:
            processed = consumer.run_once()
        except Exception:
            logger.exception("Reliable worker iteration failed")
            processed = False
        if not processed:
            stop.wait(settings.worker_poll_interval_seconds)
    logger.info("Valora reliable worker stopped: worker_id=%s", settings.worker_id)


if __name__ == "__main__":
    main()
