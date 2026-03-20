"""
REST API Routes for Execution Market

Thin aggregation layer — includes all sub-routers from api/routers/.
Backward-compatible re-exports kept for existing test imports.
"""

import sys
import types

from fastapi import APIRouter

# Sub-routers
from .routers.tasks import router as tasks_router
from .routers.submissions import router as submissions_router
from .routers.workers import router as workers_router
from .routers.misc import router as misc_router
from .routers.evidence import router as evidence_router
from .routers.payments import router as payments_router
from .routers.webhooks import router as webhooks_router
from .routers.identity import router as identity_router
from .routers.relay import router as relay_router

# ---------------------------------------------------------------------------
# Aggregated router — imported by api/__init__.py as ``api_router``
# ---------------------------------------------------------------------------
router = APIRouter()
router.include_router(tasks_router)
router.include_router(submissions_router)
router.include_router(workers_router)
router.include_router(misc_router)
router.include_router(evidence_router)
router.include_router(payments_router)
router.include_router(webhooks_router)
router.include_router(identity_router)
router.include_router(relay_router)

# ---------------------------------------------------------------------------
# Backward-compatible re-exports used by tests and jobs
# ---------------------------------------------------------------------------

# supabase_client as ``db`` — tests monkeypatch ``routes.db``
import supabase_client as db  # noqa: F401, E402

# Models re-exported from the models enum (tests access routes.TaskCategory etc.)
from models import TaskCategory, EvidenceType  # noqa: F401, E402

# Auth functions re-exported (tests monkeypatch routes.verify_agent_owns_submission)
from .auth import verify_agent_owns_submission  # noqa: F401, E402

# Pydantic request/response models imported by tests
from .routers._models import (  # noqa: F401, E402
    ApprovalRequest,
    CreateTaskRequest,
    RejectionRequest,
    WorkerApplicationRequest,
    WorkerSubmissionRequest,
)

# Endpoint functions imported directly by tests
from .routers.tasks import (  # noqa: F401, E402
    cancel_task,
    create_task,
    get_public_platform_metrics,
    get_task_payment,
    get_task_transactions,
)
from .routers.submissions import (  # noqa: F401, E402
    approve_submission,
    reject_submission,
)
from .routers.workers import (  # noqa: F401, E402
    apply_to_task,
    submit_work,
)

# Helper functions and constants imported by tests and jobs
from .routers._helpers import (  # noqa: F401, E402
    X402_AVAILABLE,
    get_payment_dispatcher,
    get_sdk,
    _build_explorer_url,
    _is_payment_finalized,
    _resolve_task_payment_header,
    _ws1_auto_register_worker,
    _ws2_auto_rate_agent,
    _execute_post_approval_side_effects,
    _is_submission_ready_for_instant_payout,
    _settle_submission_payment,
    _auto_approve_submission,
)

# ---------------------------------------------------------------------------
# Module proxy: propagate monkeypatches of ``routes.db`` to sub-routers.
#
# Tests do ``patch("api.routes.db")`` which replaces the ``db`` binding in
# this module's namespace.  Helper functions live in ``_helpers`` (and other
# sub-router modules) with their own ``db`` binding.  The proxy intercepts
# __setattr__ and propagates ``db`` changes so patched tests still work.
# ---------------------------------------------------------------------------
from .routers import _helpers as _helpers_mod  # noqa: E402
from .routers import tasks as _tasks_mod  # noqa: E402
from .routers import submissions as _submissions_mod  # noqa: E402
from .routers import workers as _workers_mod  # noqa: E402
from .routers import misc as _misc_mod  # noqa: E402
from .routers import identity as _identity_mod  # noqa: E402
from .routers import relay as _relay_mod  # noqa: E402

_SUB_MODULES = [_helpers_mod, _tasks_mod, _submissions_mod, _workers_mod, _misc_mod, _identity_mod, _relay_mod]


class _RoutesModuleProxy(types.ModuleType):
    """Transparent proxy that propagates attribute patches to sub-routers.

    Tests monkeypatch attributes on ``routes`` (e.g. ``routes.db``,
    ``routes.verify_agent_owns_submission``).  After the split, the actual
    functions/objects live in sub-modules.  This proxy forwards any
    ``setattr`` to every sub-module that already has that attribute, keeping
    backward-compatible monkeypatching working.
    """

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        # Propagate to any sub-module that has the same name
        for mod in _SUB_MODULES:
            if name in mod.__dict__:
                mod.__dict__[name] = value


_self = sys.modules[__name__]
_proxy = _RoutesModuleProxy(__name__)
_proxy.__dict__.update(_self.__dict__)
sys.modules[__name__] = _proxy
