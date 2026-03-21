"""
Chat Relay Module — WebSocket bridge between mobile clients and IRC task channels.

Components:
- models.py: Pydantic schemas (ChatMessageIn/Out, ChatError, ChatHistory)
- irc_pool.py: Singleton IRC connection multiplexed across channels
- relay.py: WebSocket endpoint at /ws/chat/{task_id}
- event_injector.py: Injects task lifecycle events as system messages

Usage in FastAPI:
    from chat import chat_router, setup_chat

    app.include_router(chat_router)
    # In lifespan:
    chat_resources = await setup_chat(event_bus)
    yield
    await teardown_chat(chat_resources)
"""

import logging

from .models import (
    ChatMessageIn,
    ChatMessageOut,
    ChatError,
    ChatHistory,
    ChatStatus,
    is_blocked_action,
)
from .relay import router as chat_router
from .irc_pool import IRCPool
from .guardrail import GuardrailFilter
from .log_service import ChatLogService, get_log_service

logger = logging.getLogger(__name__)


async def setup_chat(event_bus=None) -> dict:
    """Initialize chat subsystem. Call from FastAPI lifespan.

    Returns a dict of resources to pass to teardown_chat().
    """
    resources: dict = {"pool": None, "injector": None}

    try:
        from config.platform_config import PlatformConfig

        enabled = await PlatformConfig.get("feature.task_chat_enabled", False)
        if not enabled:
            logger.info("Task chat disabled (feature.task_chat_enabled=false)")
            return resources
    except Exception:
        logger.info("Task chat: could not check feature flag, skipping init")
        return resources

    # Initialize IRC pool
    try:
        from config.platform_config import PlatformConfig

        host = await PlatformConfig.get("chat.irc_host", "irc.meshrelay.xyz")
        port = await PlatformConfig.get("chat.irc_port", 6697)
        use_tls = await PlatformConfig.get("chat.irc_tls", True)
        nick_prefix = await PlatformConfig.get("chat.irc_nick_prefix", "em-relay")

        pool = IRCPool.get_instance(
            host=host,
            port=int(port),
            use_tls=bool(use_tls),
            nick_prefix=nick_prefix,
        )
        connected = await pool.connect()
        if connected:
            logger.info("Chat IRC pool connected: %s", pool.nick)
        else:
            logger.warning("Chat IRC pool failed to connect")
        resources["pool"] = pool
    except Exception:
        logger.exception("Failed to initialize chat IRC pool")

    # Initialize event injector
    if event_bus and resources["pool"]:
        try:
            from .event_injector import EventInjector

            injector = EventInjector(bus=event_bus)
            injector.start()
            resources["injector"] = injector
            logger.info("Chat event injector started")
        except Exception:
            logger.exception("Failed to start chat event injector")

    return resources


async def teardown_chat(resources: dict) -> None:
    """Shut down chat subsystem. Call from FastAPI lifespan."""
    injector = resources.get("injector")
    if injector:
        injector.stop()

    pool = resources.get("pool")
    if pool:
        await pool.disconnect()
        IRCPool.reset_instance()

    logger.info("Chat subsystem shut down")


__all__ = [
    "ChatMessageIn",
    "ChatMessageOut",
    "ChatError",
    "ChatHistory",
    "ChatStatus",
    "is_blocked_action",
    "chat_router",
    "IRCPool",
    "GuardrailFilter",
    "ChatLogService",
    "get_log_service",
    "setup_chat",
    "teardown_chat",
]
