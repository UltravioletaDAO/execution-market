"""
Execution Market API Router Modules

Split from the monolithic routes.py into logical groups:
- _helpers: Shared helper functions (payment, escrow, side effects)
- _models: Pydantic request/response models
- tasks: Task CRUD, batch, assign, cancel, payment timeline
- submissions: Submission approval, rejection, more-info
- workers: Worker apply and submit endpoints
- misc: Config, analytics, evidence verification, identity, auth, health
"""
