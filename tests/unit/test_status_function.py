"""Unit tests for the status Lambda function."""

import base64
import json
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest


def create_mock_jwt_token(groups=None):
    """Create a mock JWT token with specified groups."""
    if groups is None:
        groups = []

    payload = {"cognito:groups": groups, "sub": "test-user-id", "email": "test@example.com"}

    # Create a simple JWT-like token (header.payload.signature)
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).decode().rstrip("=")
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = "fake-signature"  # Simplified signature for testing

    return f"{header}.{payload_encoded}.{signature}"


@pytest.fixture
def status_mod(monkeypatch):
    """Import the status module after setting required env vars."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "test-kb-id")
    monkeypatch.setenv("DATA_SOURCE_ID", "test-ds-id")
    import importlib

    mod = importlib.import_module("functions.status.index")
    # Ensure a clean import state in case of module cache from other tests
    mod = importlib.reload(mod)
    return mod


@pytest.fixture
def status_mod_region_only(monkeypatch):
    """Import the status module with only region set (no KB/DS env)."""
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    # Ensure KB/DS are unset for this import
    monkeypatch.delenv("KNOWLEDGE_BASE_ID", raising=False)
    monkeypatch.delenv("DATA_SOURCE_ID", raising=False)
    import importlib

    mod = importlib.import_module("functions.status.index")
    mod = importlib.reload(mod)
    return mod


class TestJWTDecoding:
    """Test JWT token decoding functionality."""

    def test_decode_jwt_payload_valid_token(self, status_mod):
        """Test decoding a valid JWT token."""
        token = create_mock_jwt_token(["Admin", "User"])
        payload = status_mod.decode_jwt_payload(token)

        assert payload["cognito:groups"] == ["Admin", "User"]
        assert payload["sub"] == "test-user-id"
        assert payload["email"] == "test@example.com"

    def test_decode_jwt_payload_invalid_token(self, status_mod):
        """Test decoding an invalid JWT token."""
        invalid_token = "invalid.token.format"
        payload = status_mod.decode_jwt_payload(invalid_token)

        assert payload == {}

    def test_decode_jwt_payload_malformed_token(self, status_mod):
        """Test decoding a malformed JWT token."""
        malformed_token = "not-a-jwt-token"
        payload = status_mod.decode_jwt_payload(malformed_token)

        assert payload == {}


class TestAdminChecking:
    """Test admin group checking functionality."""

    def test_is_user_admin_with_admin_group(self, status_mod):
        """Test admin check with user in Admin group."""
        admin_token = create_mock_jwt_token(["Admin"])
        event = {"headers": {"Authorization": f"Bearer {admin_token}"}}

        assert status_mod.is_user_admin(event)

    def test_is_user_admin_without_admin_group(self, status_mod):
        """Test admin check with user not in Admin group."""
        user_token = create_mock_jwt_token(["User"])
        event = {"headers": {"Authorization": f"Bearer {user_token}"}}

        assert not status_mod.is_user_admin(event)

    def test_is_user_admin_no_groups(self, status_mod):
        """Test admin check with user having no groups."""
        user_token = create_mock_jwt_token([])
        event = {"headers": {"Authorization": f"Bearer {user_token}"}}

        assert not status_mod.is_user_admin(event)

    def test_is_user_admin_no_authorization_header(self, status_mod):
        """Test admin check with no Authorization header."""
        event = {"headers": {}}

        assert not status_mod.is_user_admin(event)

    def test_is_user_admin_invalid_authorization_header(self, status_mod):
        """Test admin check with invalid Authorization header."""
        event = {"headers": {"Authorization": "InvalidFormat"}}

        assert not status_mod.is_user_admin(event)

    def test_is_user_admin_case_insensitive_header(self, status_mod):
        """Test admin check with lowercase authorization header."""
        admin_token = create_mock_jwt_token(["Admin"])
        event = {
            "headers": {
                "authorization": f"Bearer {admin_token}"  # lowercase
            }
        }

        assert status_mod.is_user_admin(event)


class TestIngestionJobsRetrieval:
    """Test Bedrock ingestion jobs retrieval."""

    @patch("functions.status.index.bedrock_agent_client")
    def test_get_ingestion_jobs_status_success(self, mock_bedrock_client, status_mod):
        """Test successful retrieval of ingestion jobs."""
        mock_bedrock_client.list_ingestion_jobs.return_value = {
            "ingestionJobSummaries": [
                {
                    "ingestionJobId": "job-1",
                    "status": "COMPLETE",
                    "startedAt": datetime(2024, 1, 1, 0, 0, 0),
                    "updatedAt": datetime(2024, 1, 1, 1, 0, 0),
                    "description": "Test job 1",
                    "statistics": {"documentsScanned": 10},
                },
                {
                    "ingestionJobId": "job-2",
                    "status": "IN_PROGRESS",
                    "startedAt": datetime(2024, 1, 2, 0, 0, 0),
                    "updatedAt": datetime(2024, 1, 2, 0, 30, 0),
                    "description": "Test job 2",
                    "statistics": {"documentsScanned": 5},
                },
            ]
        }

        jobs = status_mod.get_ingestion_jobs_status("test-kb-id", "test-ds-id")

        assert len(jobs) == 2
        assert jobs[0]["ingestionJobId"] == "job-1"
        assert jobs[0]["status"] == "COMPLETE"
        assert jobs[1]["ingestionJobId"] == "job-2"
        assert jobs[1]["status"] == "IN_PROGRESS"

    @patch("functions.status.index.bedrock_agent_client")
    def test_get_ingestion_jobs_status_error(self, mock_bedrock_client, status_mod):
        """Test error handling in ingestion jobs retrieval."""
        mock_bedrock_client.list_ingestion_jobs.side_effect = Exception("Bedrock error")

        jobs = status_mod.get_ingestion_jobs_status("test-kb-id", "test-ds-id")

        assert jobs == []


class TestStatusHandler:
    """Test the main status handler function."""

    def test_status_handler_admin(self, status_mod):
        """Test the handler with admin user."""
        # Patch the helper function used by the handler
        with patch("functions.status.index.get_ingestion_jobs_status") as mock_get_jobs:
            mock_get_jobs.return_value = [
                {
                    "ingestionJobId": "test-job-1",
                    "status": "COMPLETE",
                    "startedAt": datetime(2024, 1, 1, 0, 0, 0).isoformat(),
                    "updatedAt": datetime(2024, 1, 1, 1, 0, 0).isoformat(),
                    "description": "Test ingestion job",
                    "statistics": {"documentsScanned": 10, "documentsIndexed": 10},
                }
            ]

            # Create admin event
            admin_token = create_mock_jwt_token(["Admin"])
            event = {"headers": {"Authorization": f"Bearer {admin_token}"}}

            # Call handler
            response = status_mod.handler(event, Mock())

            # Assert that the mocked function was called
            mock_get_jobs.assert_called_once_with("test-kb-id", "test-ds-id")

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["knowledgeBaseId"] == "test-kb-id"
            assert body["dataSourceId"] == "test-ds-id"
            assert len(body["ingestionJobs"]) == 1
            assert body["totalJobs"] == 1
            assert body["ingestionJobs"][0]["status"] == "COMPLETE"

    def test_handler_non_admin_user_denied(self, status_mod):
        """Test handler with non-admin user returns 403."""
        user_token = create_mock_jwt_token(["User"])
        event = {"headers": {"Authorization": f"Bearer {user_token}"}}

        response = status_mod.handler(event, Mock())

        assert response["statusCode"] == 403

        body = json.loads(response["body"])
        assert "Access denied" in body["error"]

    def test_handler_no_auth_denied(self, status_mod):
        """Test handler with no authorization returns 403."""
        event = {"headers": {}}

        response = status_mod.handler(event, Mock())

        assert response["statusCode"] == 403

        body = json.loads(response["body"])
        assert "Access denied" in body["error"]

    @patch.dict(os.environ, {"KNOWLEDGE_BASE_ID": "", "DATA_SOURCE_ID": ""}, clear=True)
    def test_handler_missing_config(self, status_mod_region_only):
        """Test handler with missing environment configuration returns 500."""
        admin_token = create_mock_jwt_token(["Admin"])
        event = {"headers": {"Authorization": f"Bearer {admin_token}"}}

        response = status_mod_region_only.handler(event, Mock())

        assert response["statusCode"] == 500

        body = json.loads(response["body"])
        assert "Configuration error" in body["error"]

    def test_handler_cors_headers(self, status_mod):
        """Test that all responses include proper CORS headers."""
        user_token = create_mock_jwt_token(["User"])
        event = {"headers": {"Authorization": f"Bearer {user_token}"}}

        response = status_mod.handler(event, Mock())

        assert "Access-Control-Allow-Origin" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Origin"] == "*"
        assert "Access-Control-Allow-Credentials" in response["headers"]
        assert response["headers"]["Access-Control-Allow-Credentials"] is True
