"""Sender identity for AgentSessionEvent payloads shaped like Linear's published schema.

Linear's `AgentSessionEventWebhookPayload` (linear/linear packages/sdk/src/schema.graphql)
has NO top-level `actor`. The human is `agentSession.creatorId` / `agentSession.creator`
for `created` (whoever mentioned or delegated) and `agentActivity.userId` /
`agentActivity.user` for `prompted` (whoever sent the follow-up). These tests pin that
the adapter-layer authorization sees the real sender — and, for `prompted`, the sender of
the message rather than the session's original creator.
"""

from __future__ import annotations

import time

from hermes_linear_agent.webhook import extract_context, is_authorized

OWNER = "db172fde-8963-4d93-9eb3-a579bd68c768"
STRANGER = "0badc0de-0000-4000-8000-000000000000"
TEAM = "6e34243a-2cd7-4091-97ef-61733c904cea"


def _session(creator_id: str | None) -> dict:
    session = {
        "id": "session-1",
        "appUserId": "app-user-1",
        "organizationId": "org-1",
        "status": "pending",
        "type": "commentThread",
        "createdAt": "2026-09-28T12:24:12.000Z",
        "updatedAt": "2026-09-28T12:24:12.000Z",
        "issueId": "issue-1",
        "issue": {"id": "issue-1", "identifier": "011-1", "title": "Test", "team": {"id": TEAM}},
        "commentId": "comment-1",
        "comment": {"id": "comment-1", "body": "@Donna summarise this issue in one sentence"},
    }
    if creator_id is not None:
        session["creatorId"] = creator_id
        session["creator"] = {"id": creator_id, "name": "roaanv"}
    return session


def _created(creator_id: str | None) -> dict:
    return {
        "type": "AgentSessionEvent",
        "action": "created",
        "appUserId": "app-user-1",
        "oauthClientId": "client-1",
        "organizationId": "org-1",
        "createdAt": "2026-09-28T12:24:12.000Z",
        "webhookId": "webhook-1",
        "webhookTimestamp": int(time.time() * 1000),
        "agentSession": _session(creator_id),
    }


def _prompted(*, creator_id: str, prompter_id: str | None) -> dict:
    activity = {
        "id": "activity-1",
        "agentSessionId": "session-1",
        "content": {"type": "prompt", "body": "and list the next steps"},
        "createdAt": "2026-09-28T12:25:00.000Z",
        "updatedAt": "2026-09-28T12:25:00.000Z",
    }
    if prompter_id is not None:
        activity["userId"] = prompter_id
        activity["user"] = {"id": prompter_id, "name": "someone"}
    payload = _created(creator_id)
    payload["action"] = "prompted"
    payload["agentActivity"] = activity
    return payload


def _authorized(payload: dict) -> bool:
    context = extract_context(payload, {})
    return is_authorized(context, allowed_users=[OWNER], allowed_teams=[TEAM])


def test_created_session_sender_is_session_creator():
    context = extract_context(_created(OWNER), {})
    assert context.actor_user_id == OWNER


def test_created_session_by_allowlisted_creator_is_authorized():
    assert _authorized(_created(OWNER)) is True


def test_created_session_by_other_creator_is_denied():
    assert _authorized(_created(STRANGER)) is False


def test_created_session_without_creator_is_denied():
    assert _authorized(_created(None)) is False


def test_prompted_sender_is_activity_user():
    context = extract_context(_prompted(creator_id=OWNER, prompter_id=OWNER), {})
    assert context.actor_user_id == OWNER


def test_prompted_by_allowlisted_user_is_authorized():
    assert _authorized(_prompted(creator_id=OWNER, prompter_id=OWNER)) is True


def test_prompted_by_stranger_in_owners_session_is_denied():
    """Security: a follow-up is authorized on who SENT it, never on who created the session."""
    assert _authorized(_prompted(creator_id=OWNER, prompter_id=STRANGER)) is False


def test_prompted_without_activity_user_does_not_fall_back_to_creator():
    """Fail closed: a prompt with no identifiable sender must not inherit the creator's rights."""
    assert _authorized(_prompted(creator_id=OWNER, prompter_id=None)) is False
