from datetime import datetime, timezone

from app import create_app
from app.auth.utils import hash_password
from app.extensions.db import db
from app.models.audit_log import AuditLog
from app.models.ticket import Ticket
from app.models.ticket_reply import TicketReply
from app.models.user import User
from tests.conftest import TestConfig, login


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def login_headers(client, email, password):
    return auth_header(login(client, email, password))


def create_ticket(client, headers, title="Cannot login", description="Login keeps failing on the portal", **extra):
    payload = {"title": title, "description": description, **extra}
    response = client.post("/tickets", headers=headers, json=payload)
    assert response.status_code == 201
    return response.get_json()["data"]


def assign_ticket(client, ticket_id, agent_id=2):
    admin_headers = login_headers(client, "admin@example.com", "Admin@123")
    response = client.patch(f"/tickets/{ticket_id}/assign", headers=admin_headers, json={"agent_id": agent_id})
    assert response.status_code == 200
    return response.get_json()["data"]


def test_customer_can_create_ticket_and_admin_can_assign(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    ticket = create_ticket(client, customer_headers, priority="high")

    response = client.patch(f"/tickets/{ticket['id']}/assign", headers=login_headers(client, "admin@example.com", "Admin@123"), json={"agent_id": 2})
    assert response.status_code == 200
    assert response.get_json()["data"]["assigned_agent_id"] == 2


def test_agent_can_resolve_assigned_ticket(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    ticket = create_ticket(client, customer_headers, title="Payment failed", description="Payment failed during checkout")

    assign_ticket(client, ticket["id"])

    response = client.patch(
        f"/tickets/{ticket['id']}/status",
        headers=login_headers(client, "agent@example.com", "Agent@123"),
        json={"status": "resolved"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "resolved"


def test_customer_cannot_list_all_tickets(client):
    response = client.get("/tickets", headers=login_headers(client, "customer@example.com", "Customer@123"))
    assert response.status_code == 403


def test_customer_can_update_own_ticket(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    ticket = create_ticket(client, customer_headers, title="Old title", description="A detailed old description")

    response = client.patch(
        f"/tickets/{ticket['id']}",
        headers=customer_headers,
        json={"title": "Updated title", "priority": "urgent"},
    )
    assert response.status_code == 200
    body = response.get_json()["data"]
    assert body["title"] == "Updated title"
    assert body["priority"] == "urgent"


def test_authentication_registration_refresh_logout_and_password_reset(client, monkeypatch):
    response = client.post(
        "/auth/register",
        json={
            "name": "New Customer",
            "email": "NEW@example.com",
            "password": "Customer@456",
            "phone_number": "+2348012345678",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["email"] == "new@example.com"

    login_response = client.post("/auth/login", json={"email": "new@example.com", "password": "Customer@456"})
    tokens = login_response.get_json()["data"]
    assert login_response.status_code == 200
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refresh_response = client.post("/auth/refresh", headers=auth_header(tokens["refresh_token"]))
    assert refresh_response.status_code == 200
    assert refresh_response.get_json()["data"]["access_token"]

    logout_response = client.post("/auth/logout", headers=auth_header(tokens["access_token"]))
    assert logout_response.status_code == 200
    revoked_response = client.get("/tickets/my-tickets", headers=auth_header(tokens["access_token"]))
    assert revoked_response.status_code == 401

    reset_token = "KnownReset@123"

    def fake_reset_token(user):
        user.reset_token_hash = hash_password(reset_token)
        user.reset_token_expires_at = datetime(2099, 1, 1, tzinfo=timezone.utc)
        return reset_token

    monkeypatch.setattr("app.auth.service.make_reset_token", fake_reset_token)
    forgot_response = client.post("/auth/forgot-password", json={"email": "new@example.com"})
    assert forgot_response.status_code == 200

    reset_response = client.post(
        "/auth/reset-password",
        json={"email": "new@example.com", "token": reset_token, "password": "Customer@789"},
    )
    assert reset_response.status_code == 200, reset_response.get_json()
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "Customer@789"}).status_code == 200


def test_user_management_apis_for_admin(client):
    admin_headers = login_headers(client, "admin@example.com", "Admin@123")

    create_response = client.post(
        "/users/agents",
        headers=admin_headers,
        json={"name": "Second Agent", "email": "agent2@example.com", "password": "Agent@456"},
    )
    assert create_response.status_code == 201
    agent = create_response.get_json()["data"]
    assert agent["role"] == "agent"

    list_response = client.get("/users", headers=admin_headers)
    assert list_response.status_code == 200
    assert any(user["email"] == "agent2@example.com" for user in list_response.get_json()["data"])

    detail_response = client.get(f"/users/{agent['id']}", headers=admin_headers)
    assert detail_response.status_code == 200
    assert detail_response.get_json()["data"]["email"] == "agent2@example.com"

    update_response = client.put(
        f"/users/{agent['id']}",
        headers=admin_headers,
        json={"name": "Updated Agent", "phone_number": "+2348099999999", "is_active": True},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["data"]["name"] == "Updated Agent"

    delete_response = client.delete(f"/users/{agent['id']}", headers=admin_headers)
    assert delete_response.status_code == 200
    assert client.get(f"/users/{agent['id']}", headers=admin_headers).get_json()["data"]["is_active"] is False


def test_ticket_status_close_and_reopen_workflow(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    admin_headers = login_headers(client, "admin@example.com", "Admin@123")
    agent_headers = login_headers(client, "agent@example.com", "Agent@123")
    ticket = create_ticket(client, customer_headers, title="Workflow issue", description="Workflow needs full testing")

    assigned = assign_ticket(client, ticket["id"])
    assert assigned["status"] == "in_progress"

    bad_transition = client.patch(f"/tickets/{ticket['id']}/status", headers=agent_headers, json={"status": "closed"})
    assert bad_transition.status_code == 400

    resolved = client.patch(f"/tickets/{ticket['id']}/status", headers=agent_headers, json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.get_json()["data"]["status"] == "resolved"

    closed = client.patch(f"/tickets/{ticket['id']}/close", headers=admin_headers)
    assert closed.status_code == 200
    assert closed.get_json()["data"]["status"] == "closed"

    blocked_update = client.patch(f"/tickets/{ticket['id']}", headers=customer_headers, json={"title": "Blocked"})
    assert blocked_update.status_code == 400

    reopened = client.patch(f"/tickets/{ticket['id']}/reopen", headers=admin_headers)
    assert reopened.status_code == 200
    assert reopened.get_json()["data"]["status"] == "open"


def test_replies_conversation_history_and_timestamps(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    agent_headers = login_headers(client, "agent@example.com", "Agent@123")
    ticket = create_ticket(client, customer_headers, title="Reply test", description="Conversation history should work")
    assign_ticket(client, ticket["id"])

    customer_reply = client.post(
        f"/tickets/{ticket['id']}/replies",
        headers=customer_headers,
        json={"message": "Here is more information."},
    )
    assert customer_reply.status_code == 201

    agent_reply = client.post(
        f"/tickets/{ticket['id']}/replies",
        headers=agent_headers,
        json={"message": "Thanks, I am checking it."},
    )
    assert agent_reply.status_code == 201

    history = client.get(f"/tickets/{ticket['id']}/replies", headers=customer_headers)
    assert history.status_code == 200
    messages = history.get_json()["data"]
    assert [message["message"] for message in messages] == ["Here is more information.", "Thanks, I am checking it."]
    assert all(message["created_at"] for message in messages)


def test_dashboard_statistics(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    admin_headers = login_headers(client, "admin@example.com", "Admin@123")
    agent_headers = login_headers(client, "agent@example.com", "Agent@123")

    open_ticket = create_ticket(client, customer_headers, title="Open stats", description="Open ticket for stats")
    resolved_ticket = create_ticket(client, customer_headers, title="Resolved stats", description="Resolved ticket for stats")
    closed_ticket = create_ticket(client, customer_headers, title="Closed stats", description="Closed ticket for stats")

    assign_ticket(client, resolved_ticket["id"])
    client.patch(f"/tickets/{resolved_ticket['id']}/status", headers=agent_headers, json={"status": "resolved"})

    assign_ticket(client, closed_ticket["id"])
    client.patch(f"/tickets/{closed_ticket['id']}/status", headers=agent_headers, json={"status": "resolved"})
    client.patch(f"/tickets/{closed_ticket['id']}/close", headers=admin_headers)

    response = client.get("/dashboard/stats", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["total_tickets"] == 3
    assert data["open_tickets"] == 1
    assert data["resolved_tickets"] == 1
    assert data["closed_tickets"] == 1
    assert data["active_agents"] == 1
    assert open_ticket["status"] == "open"


def test_search_and_filtering(client):
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    admin_headers = login_headers(client, "admin@example.com", "Admin@123")
    first = create_ticket(
        client,
        customer_headers,
        title="Printer broken",
        description="The office printer cannot print tickets",
        priority="urgent",
    )
    second = create_ticket(
        client,
        customer_headers,
        title="Email bounce",
        description="Support emails are bouncing repeatedly",
        priority="low",
    )
    assign_ticket(client, second["id"])

    title_response = client.get("/tickets?title=Printer", headers=admin_headers)
    assert title_response.status_code == 200
    assert [ticket["id"] for ticket in title_response.get_json()["data"]] == [first["id"]]

    customer_response = client.get("/tickets?customer=Customer", headers=admin_headers)
    assert customer_response.status_code == 200
    assert {ticket["id"] for ticket in customer_response.get_json()["data"]} == {first["id"], second["id"]}

    status_response = client.get("/tickets?status=in_progress", headers=admin_headers)
    assert status_response.status_code == 200
    assert [ticket["id"] for ticket in status_response.get_json()["data"]] == [second["id"]]

    agent_response = client.get("/tickets?agent=2", headers=admin_headers)
    assert agent_response.status_code == 200
    assert [ticket["id"] for ticket in agent_response.get_json()["data"]] == [second["id"]]

    date_response = client.get(f"/tickets?date={first['created_at'][:10]}", headers=admin_headers)
    assert date_response.status_code == 200
    assert {ticket["id"] for ticket in date_response.get_json()["data"]} == {first["id"], second["id"]}


def test_validation_error_handling_authorization_and_sanitization(client):
    invalid_register = client.post("/auth/register", json={"name": "", "email": "bad", "password": "weak"})
    assert invalid_register.status_code == 400
    assert {"name", "email", "password"} <= set(invalid_register.get_json()["errors"])

    unauthenticated = client.get("/tickets/my-tickets")
    assert unauthenticated.status_code == 401

    agent_headers = login_headers(client, "agent@example.com", "Agent@123")
    forbidden = client.post("/tickets", headers=agent_headers, json={"title": "Agent ticket", "description": "Not allowed"})
    assert forbidden.status_code == 403

    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    invalid_ticket = client.post("/tickets", headers=customer_headers, json={"title": "No", "description": "short"})
    assert invalid_ticket.status_code == 400

    sanitized_ticket = create_ticket(
        client,
        customer_headers,
        title="  Trimmed title  ",
        description="  Description should be stripped  ",
    )
    assert sanitized_ticket["title"] == "Trimmed title"
    assert sanitized_ticket["description"] == "Description should be stripped"

    admin_headers = login_headers(client, "admin@example.com", "Admin@123")
    bad_date = client.get("/tickets?date=26-06-2026", headers=admin_headers)
    assert bad_date.status_code == 400


def test_bonus_email_notifications_priority_levels_and_audit_logs(client, app, monkeypatch):
    sent_messages = []

    def collect_email(to, subject, body):
        sent_messages.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr("app.tickets.service.send_email", collect_email)
    customer_headers = login_headers(client, "customer@example.com", "Customer@123")
    agent_headers = login_headers(client, "agent@example.com", "Agent@123")
    ticket = create_ticket(
        client,
        customer_headers,
        title="Priority issue",
        description="Urgent ticket should store its priority",
        priority="urgent",
    )
    assign_ticket(client, ticket["id"])
    client.patch(f"/tickets/{ticket['id']}/status", headers=agent_headers, json={"status": "resolved"})

    assert [message["subject"] for message in sent_messages] == ["Ticket Created", "Ticket Assigned", "Ticket Resolved"]

    with app.app_context():
        stored_ticket = db.session.get(Ticket, ticket["id"])
        assert stored_ticket.priority == "urgent"
        assert AuditLog.query.filter_by(entity_type="ticket", entity_id=ticket["id"]).count() >= 3


def test_database_schema_stores_required_fields(app):
    user_columns = set(User.__table__.columns.keys())
    ticket_columns = set(Ticket.__table__.columns.keys())
    reply_columns = set(TicketReply.__table__.columns.keys())

    assert {"name", "email", "role", "phone_number", "created_at"} <= user_columns
    assert {
        "ticket_number",
        "title",
        "description",
        "customer_id",
        "assigned_agent_id",
        "status",
        "created_at",
        "updated_at",
    } <= ticket_columns
    assert {"ticket_id", "message", "user_id", "created_at"} <= reply_columns


def test_api_documentation_and_submission_deliverables_exist(client):
    assert client.get("/apidocs/").status_code == 200
    assert client.get("/apispec_1.json").status_code == 200


def test_rate_limiting_blocks_repeated_requests():
    class RateLimitTestConfig(TestConfig):
        RATE_LIMIT_ENABLED = True
        RATE_LIMIT_REQUESTS = 2
        RATE_LIMIT_WINDOW_SECONDS = 60

    app = create_app(RateLimitTestConfig)
    client = app.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 200

    response = client.get("/")
    assert response.status_code == 429
    assert response.get_json()["message"] == "Too many requests. Please try again later."
    assert response.headers["Retry-After"]
