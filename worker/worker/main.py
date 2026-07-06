import logging

from worker.config import get_worker_settings


def main() -> None:
    settings = get_worker_settings()
    logging.basicConfig(level=getattr(logging, settings.valora_log_level.upper(), logging.INFO))
    logging.info("Valora worker started: phase=engineering-sprint-0 env=%s", settings.valora_env)
    logging.info("No business jobs are registered in Sprint 0.")


if __name__ == "__main__":
    main()
