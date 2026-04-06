import unittest
from unittest.mock import Mock, patch

import requests

import src.app_state as app_state
from src.api_client import (
    ApiError,
    login,
    register,
    get_components,
    create_project,
    update_project,
    delete_project,
)


class ApiClientTests(unittest.TestCase):
    def setUp(self):
        self.base_url_patch = patch.object(app_state, "BACKEND_BASE_URL", "http://example.com")
        self.token_patch = patch.object(app_state, "access_token", "test-token")
        self.base_url_patch.start()
        self.token_patch.start()
        self.addCleanup(self.base_url_patch.stop)
        self.addCleanup(self.token_patch.stop)

    @patch("src.api_client.requests.post")
    def test_login_success_returns_tokens(self, mock_post):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"access": "access-token", "refresh": "refresh-token"}
        mock_post.return_value = mock_response

        access, refresh = login("alice", "secret")

        self.assertEqual(access, "access-token")
        self.assertEqual(refresh, "refresh-token")
        mock_post.assert_called_once()

    @patch("src.api_client.requests.post")
    def test_login_failure_raises_api_error(self, mock_post):
        mock_response = Mock(status_code=401)
        mock_response.json.return_value = {"detail": "Invalid credentials."}
        mock_post.return_value = mock_response

        with self.assertRaises(ApiError) as ctx:
            login("alice", "wrong")

        self.assertIn("Invalid credentials", str(ctx.exception))

    @patch("src.api_client.requests.post", side_effect=requests.RequestException("offline"))
    def test_login_network_error_raises_api_error(self, mock_post):
        with self.assertRaises(ApiError) as ctx:
            login("alice", "secret")

        self.assertIn("Could not reach server", str(ctx.exception))

    @patch("src.api_client.requests.post")
    def test_register_success_returns_response_json(self, mock_post):
        mock_response = Mock(status_code=201)
        mock_response.json.return_value = {"message": "User registered successfully"}
        mock_post.return_value = mock_response

        result = register("alice", "alice@example.com", "secret")

        self.assertEqual(result["message"], "User registered successfully")

    @patch("src.api_client.requests.post")
    def test_register_failure_raises_api_error(self, mock_post):
        mock_response = Mock(status_code=400)
        mock_response.json.return_value = {"message": "Username already exists"}
        mock_post.return_value = mock_response

        with self.assertRaises(ApiError) as ctx:
            register("alice", "alice@example.com", "secret")

        self.assertIn("Username already exists", str(ctx.exception))

    @patch("src.api_client.requests.post")
    def test_register_edge_when_response_body_is_not_json(self, mock_post):
        mock_response = Mock(status_code=500)
        mock_response.json.side_effect = ValueError("bad json")
        mock_post.return_value = mock_response

        with self.assertRaises(ApiError) as ctx:
            register("alice", "alice@example.com", "secret")

        self.assertIn("Registration failed", str(ctx.exception))

    @patch("src.api_client.requests.get")
    def test_get_components_returns_component_list(self, mock_get):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"components": [{"name": "Pump"}]}
        mock_get.return_value = mock_response

        components = get_components()

        self.assertEqual(components, [{"name": "Pump"}])
        mock_get.assert_called_once()

    @patch("src.api_client.requests.get")
    def test_get_components_returns_empty_list_on_unexpected_payload(self, mock_get):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"unexpected": True}
        mock_get.return_value = mock_response

        self.assertEqual(get_components(), [])

    @patch("src.api_client.requests.post")
    def test_create_project_success_returns_project(self, mock_post):
        mock_response = Mock(status_code=201)
        mock_response.json.return_value = {"project": {"id": 7, "name": "Demo"}}
        mock_post.return_value = mock_response

        project = create_project("Demo", "desc")

        self.assertEqual(project, {"id": 7, "name": "Demo"})

    @patch("src.api_client.requests.post")
    def test_create_project_failure_returns_none(self, mock_post):
        mock_response = Mock(status_code=400)
        mock_response.text = "bad request"
        mock_post.return_value = mock_response

        self.assertIsNone(create_project("", "desc"))

    @patch("src.api_client.requests.put")
    def test_update_project_success_returns_json(self, mock_put):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"status": "success"}
        mock_put.return_value = mock_response

        result = update_project(5, name="Updated")

        self.assertEqual(result, {"status": "success"})

    @patch("src.api_client.requests.put")
    def test_update_project_failure_returns_none(self, mock_put):
        mock_response = Mock(status_code=500)
        mock_response.text = "server error"
        mock_put.return_value = mock_response

        self.assertIsNone(update_project(5, name="Updated") )

    @patch("src.api_client.requests.delete")
    def test_delete_project_success_returns_json(self, mock_delete):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {"status": "success"}
        mock_delete.return_value = mock_response

        self.assertEqual(delete_project(5), {"status": "success"})

    @patch("src.api_client.requests.delete")
    def test_delete_project_failure_returns_none(self, mock_delete):
        mock_response = Mock(status_code=404)
        mock_delete.return_value = mock_response

        self.assertIsNone(delete_project(5))


if __name__ == "__main__":
    unittest.main()
