"""MoonPay Headless Onramp integration (spike — Phase 1D).

Bootstraps server-side session creation and webhook verification for the
`@moonpay/platform` SDK that the frontend mounts. Mirrors the shape of
integrations/veryai/ but speaks MoonPay's REST + HMAC webhook protocol.
"""
