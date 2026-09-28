# Changelog

All notable changes to this project will be documented here.

## Unreleased

### Fixed

- Keep the active adapter in process-wide state so `linear_agent_*` tools keep working after Hermes re-imports the plugin. A forced plugin rediscovery in a running gateway re-executes the package: the connected adapter held the old `registry` module while tools registered by the new load saw an empty one, so every tool call failed with "linear_agent platform is not currently connected" while the platform was connected. Standard library only; no private Hermes APIs.
- Identify the sender of real Linear Agent Session webhooks. Linear's `AgentSessionEventWebhookPayload` has no top-level `actor`; the human is `agentSession.creatorId`/`creator` for `created` and `agentActivity.userId`/`user` for `prompted`. The adapter only looked at `actor.id` and friends, so every genuine session had an empty sender and was denied by the (fail-closed) allowlist — Linear then showed "failed to start". A `prompted` event is authorized on the message's sender only, never on the session creator.
- Allow Python 3.14: `requires-python` widened to `>=3.11,<3.15` (Hermes now ships a 3.14 runtime and `hermes plugins enable` refused to resolve the plugin). The full test suite passes on 3.14.7 against current Hermes. (CI matrix still 3.11–3.13; adding 3.14 is a follow-up.)

### Security

- Close a webhook replay bypass. Linear signs the request body only, but when any timestamp header was present the freshness check used that unsigned header and skipped the signed `webhookTimestamp` body field, so a captured delivery could be replayed indefinitely by attaching a fresh `Linear-Timestamp`. The body `webhookTimestamp` is now always enforced (±60 s), and a delivery without a parseable one is rejected (fail closed).
- Deduplicate on a SHA-256 of the signed body in addition to the delivery id. Delivery-id headers are unsigned, so a replay inside the freshness window could previously evade dedup by sending a new `Linear-Delivery` value.

## 0.4.2 — 2026-07-29

### Fixed

- Resolve a child `AgentSession.sourceCommentId` to its root comment before replying; Linear rejects child comments as `commentCreate.parentId` with `incorrect parent`.
- Mirror final Agent Session responses to the resolved source thread in adapter-controlled delivery instead of relying on the model to invoke a comment tool.

## 0.4.1 — 2026-07-29

### Fixed

- Preserve Linear's current `agentSession.sourceCommentId` webhook field so replies triggered from an existing issue-comment thread can be routed back to that original thread.
- Accept `agentActivity.sourceCommentId` as a compatible fallback for prompted activity payloads.

## 0.4.0 — 2026-07-29

### Added

- Standalone Hermes platform-plugin distribution for Linear Agent Sessions.
- Git-directory plugin manifest and pip entry point.
- 58 attributed `linear_agent_*` tools with fail-closed mutation policies.
- Linear client-credentials and authorization-code OAuth support.
- Signed webhook handling, replay protection, Agent Activities, plans, session links, clarification, stop signals, and standalone cron delivery.
- Plugin-owned, process-locked, atomic OAuth state storage with POSIX mode `0600`.
- Read-only migration fallback for earlier `providers.linear_agent` state in Hermes `auth.json`.
- Compatibility tests for current Hermes upstream and Python 3.11–3.13.
