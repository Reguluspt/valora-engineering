"""Production consumer for Valora durable task jobs."""
from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.modules.workflow_workbench.application.reliable_job_service import (
    claim_next_job,
    complete_job,
    fail_job,
    renew_job_lease,
)

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], Session]


@dataclass(frozen=True)
class JobExecutionContext:
    organization_id: uuid.UUID
    job_id: uuid.UUID
    attempt_id: uuid.UUID
    attempt_no: int
    generation_token: int
    job_type: str
    payload: Mapping[str, Any]
    correlation_id: str | None
    causation_id: str | None


JobHandler = Callable[[JobExecutionContext], dict[str, Any]]


class JobHandlerFailure(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)


class _LeaseHeartbeat:
    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        context: JobExecutionContext,
        worker_id: str,
        lease_duration_seconds: int,
        interval_seconds: float,
    ) -> None:
        self._session_factory = session_factory
        self._context = context
        self._worker_id = worker_id
        self._lease_duration_seconds = lease_duration_seconds
        self._interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> _LeaseHeartbeat:
        self._thread = threading.Thread(
            target=self._run,
            name=f"valora-lease-{self._context.job_id}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self._interval_seconds + 1.0))

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            session = self._session_factory()
            try:
                renew_job_lease(
                    session,
                    worker_id=self._worker_id,
                    job_id=self._context.job_id,
                    org_id=self._context.organization_id,
                    attempt_id=self._context.attempt_id,
                    generation_token=self._context.generation_token,
                    lease_duration_seconds=self._lease_duration_seconds,
                )
            except Exception:
                session.rollback()
                logger.exception(
                    "Lease heartbeat failed for job=%s generation=%s",
                    self._context.job_id,
                    self._context.generation_token,
                )
            finally:
                session.close()


class ReliableJobWorker:
    """Claim, dispatch and finalize one durable job at a time."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        handlers: Mapping[str, JobHandler],
        worker_id: str,
        lease_duration_seconds: int = 300,
        heartbeat_interval_seconds: float | None = None,
        retry_base_seconds: int = 5,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id is required")
        if lease_duration_seconds < 3:
            raise ValueError("lease_duration_seconds must be at least 3")
        interval = heartbeat_interval_seconds or max(1.0, lease_duration_seconds / 3)
        if interval <= 0 or interval >= lease_duration_seconds:
            raise ValueError("heartbeat interval must be positive and shorter than the lease")
        self._session_factory = session_factory
        self._handlers = dict(handlers)
        self._worker_id = worker_id.strip()
        self._lease_duration_seconds = lease_duration_seconds
        self._heartbeat_interval_seconds = interval
        self._retry_base_seconds = retry_base_seconds

    def run_once(self) -> bool:
        """Process at most one due job; return whether a job was claimed."""
        claim_session = self._session_factory()
        try:
            claimed = claim_next_job(
                claim_session,
                worker_id=self._worker_id,
                lease_duration_seconds=self._lease_duration_seconds,
            )
            if claimed is None:
                return False
            job, attempt = claimed
            context = JobExecutionContext(
                organization_id=job.organization_id,
                job_id=job.id,
                attempt_id=attempt.id,
                attempt_no=attempt.attempt_no,
                generation_token=job.generation_token,
                job_type=job.job_type,
                payload=dict(job.payload),
                correlation_id=job.correlation_id,
                causation_id=job.causation_id,
            )
        finally:
            claim_session.close()

        handler = self._handlers.get(context.job_type)
        if handler is None:
            self._record_failure(
                context,
                error_code="unsupported_job_type",
                error_message=f"No worker handler is registered for {context.job_type}.",
            )
            return True

        try:
            with _LeaseHeartbeat(
                session_factory=self._session_factory,
                context=context,
                worker_id=self._worker_id,
                lease_duration_seconds=self._lease_duration_seconds,
                interval_seconds=self._heartbeat_interval_seconds,
            ):
                result = handler(context)
            if not isinstance(result, dict):
                raise TypeError("Job handler result must be a JSON object.")
        except JobHandlerFailure as exc:
            logger.warning(
                "Job handler rejected source: job=%s type=%s code=%s",
                context.job_id,
                context.job_type,
                exc.code,
            )
            self._record_failure(
                context,
                error_code=exc.code,
                error_message=exc.message,
                retryable=exc.retryable,
            )
            return True
        except Exception as exc:
            logger.exception(
                "Job handler failed: job=%s type=%s generation=%s",
                context.job_id,
                context.job_type,
                context.generation_token,
            )
            self._record_failure(
                context,
                error_code="job_handler_failed",
                error_message=f"{type(exc).__name__}: {exc}",
            )
            return True

        completion_session = self._session_factory()
        try:
            complete_job(
                completion_session,
                worker_id=self._worker_id,
                job_id=context.job_id,
                org_id=context.organization_id,
                attempt_id=context.attempt_id,
                generation_token=context.generation_token,
                result_payload=result,
            )
        finally:
            completion_session.close()
        return True

    def _record_failure(
        self,
        context: JobExecutionContext,
        *,
        error_code: str,
        error_message: str,
        retryable: bool = True,
    ) -> None:
        failure_session = self._session_factory()
        try:
            fail_job(
                failure_session,
                worker_id=self._worker_id,
                job_id=context.job_id,
                org_id=context.organization_id,
                attempt_id=context.attempt_id,
                generation_token=context.generation_token,
                error_code=error_code,
                error_message=error_message,
                retry_base_seconds=self._retry_base_seconds,
                retryable=retryable,
            )
        finally:
            failure_session.close()
