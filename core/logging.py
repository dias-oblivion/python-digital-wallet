"""structlog em JSON, com o logging da stdlib (uvicorn incluso) passando pelo mesmo pipeline.

Sem dependência de framework web: o middleware que popula o `request_id` fica em
`api/middleware.py`, do lado de fora.
"""

import logging
import sys

import structlog
from structlog.types import EventDict, Processor


def _drop_color_message_key(_: object, __: str, event_dict: EventDict) -> EventDict:
    """uvicorn duplica a mensagem em `color_message`; não serve para log estruturado."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _drop_color_message_key,
    ]
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *shared,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # tudo que passa pelo logging da stdlib é renderizado pelo mesmo formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.getLevelNamesMapping()[level.upper()])

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
