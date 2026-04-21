from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import unittest
import json

from api.models import Component, Project, CanvasState, Connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(username="testuser", password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def make_png_file(name="test.png"):
    """Generate a real 1x1 red PNG so Django's ImageField validation passes."""
    import struct, zlib
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
        + chunk(b"IEND", b"")
    )
    return SimpleUploadedFile(name, png, content_type="image/png")


def make_svg_file(name="test.svg"):
    return SimpleUploadedFile(name, b"<svg xmlns='http://www.w3.org/2000/svg'/>", content_type="image/svg+xml")


def make_component(user=None, s_no="C001", name="Resistor"):
    """Create a component with valid image files."""
    return Component.objects.create(
        s_no=s_no,
        parent="Passive",
        name=name,
        svg=make_svg_file(),
        png=make_png_file(),
        created_by=user,
    )


def make_project(user, name="My Project"):
    return Project.objects.create(name=name, user=user)


def make_canvas_item(project, component, sequence=0, x=10, y=20):
    return CanvasState.objects.create(
        project=project,
        component=component,
        label="Item A",
        x=x,
        y=y,
        width=50,
        height=50,
        sequence=sequence,
    )


# ---------------------------------------------------------------------------
# Auth – Register
# ---------------------------------------------------------------------------

class RegisterViewTests(APITestCase):
    url = "/api/auth/register/"

    def test_register_success(self):
        data = {"username": "alice", "email": "alice@example.com", "password": "secret"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["username"], "alice")
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_register_duplicate_username(self):
        make_user("alice")
        data = {"username": "alice", "password": "newpass"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_register_missing_password(self):
        data = {"username": "bob"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_username(self):
        data = {"password": "secret"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_is_hashed(self):
        data = {"username": "bob", "email": "bob@example.com", "password": "plaintext"}
        self.client.post(self.url, data)
        user = User.objects.get(username="bob")
        self.assertNotEqual(user.password, "plaintext")
        self.assertTrue(user.password.startswith("pbkdf2_") or user.password.startswith("bcrypt"))


# ---------------------------------------------------------------------------
# Auth – Login / Token
# ---------------------------------------------------------------------------

class LoginViewTests(APITestCase):
    url = "/api/auth/login/"

    def setUp(self):
        self.user = make_user("carol", "pass1234")
        try:
            from axes.models import AccessAttempt
            AccessAttempt.objects.all().delete()
        except ImportError:
            pass

    def test_login_returns_tokens(self):
        response = self.client.post(self.url, {"username": "carol", "password": "pass1234"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password(self):
        response = self.client.post(self.url, {"username": "carol", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_user(self):
        response = self.client.post(self.url, {"username": "nobody", "password": "x"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Hello World
# ---------------------------------------------------------------------------

class HelloWorldTests(APITestCase):
    url = "/api/hello/"

    def test_hello_world_no_auth_required(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Hello from DRF!")


# ---------------------------------------------------------------------------
# Components – List / Create
# ---------------------------------------------------------------------------

class ComponentListViewTests(APITestCase):
    url = "/api/components/"

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def test_list_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_and_default_components(self):
        other_user = make_user("other")
        own = make_component(self.user, s_no="C001", name="OwnComp")
        default = make_component(None, s_no="C002", name="DefaultComp")
        make_component(other_user, s_no="C003", name="OtherComp")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [c["name"] for c in response.data["components"]]
        self.assertIn("OwnComp", names)
        self.assertIn("DefaultComp", names)
        self.assertNotIn("OtherComp", names)

    def test_list_excludes_components_without_svg_or_png(self):
        # Component without files
        Component.objects.create(s_no="C099", parent="X", name="NoFiles", created_by=self.user)
        response = self.client.get(self.url)
        names = [c["name"] for c in response.data["components"]]
        self.assertNotIn("NoFiles", names)

    def test_create_component(self):
        data = {
            "s_no": "C010",
            "parent": "Active",
            "name": "NewComp",
            "svg": make_svg_file("c.svg"),
            "png": make_png_file("c.png"),
        }
        response = self.client.post(self.url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comp = Component.objects.get(s_no="C010")
        self.assertEqual(comp.created_by, self.user)

    def test_create_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# Components – Detail (Retrieve / Update / Destroy)
# ---------------------------------------------------------------------------

class ComponentDetailViewTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.comp = make_component(self.user, s_no="C001", name="MyComp")

    def detail_url(self, pk):
        return f"/api/components/{pk}/"

    def test_retrieve_own_component(self):
        response = self.client.get(self.detail_url(self.comp.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "MyComp")

    def test_retrieve_default_component(self):
        default = make_component(None, s_no="D001", name="Default")
        response = self.client.get(self.detail_url(default.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_other_user_component_returns_404(self):
        other = make_user("other")
        other_comp = make_component(other, s_no="O001", name="OtherComp")
        response = self.client.get(self.detail_url(other_comp.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_own_component(self):
        response = self.client.patch(
            self.detail_url(self.comp.id),
            {"name": "UpdatedComp", "svg": make_svg_file("u.svg"), "png": make_png_file("u.png")},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comp.refresh_from_db()
        self.assertEqual(self.comp.name, "UpdatedComp")

    def test_destroy_own_component(self):
        response = self.client.delete(self.detail_url(self.comp.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Component.objects.filter(id=self.comp.id).exists())

    def test_destroy_default_component_forbidden(self):
        default = make_component(None, s_no="D002", name="DefaultComp")
        response = self.client.delete(self.detail_url(default.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Component.objects.filter(id=default.id).exists())


# ---------------------------------------------------------------------------
# Projects – List / Create
# ---------------------------------------------------------------------------

class ProjectListCreateViewTests(APITestCase):
    url = "/api/project/"

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def test_list_requires_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_own_projects(self):
        make_project(self.user, "Mine")
        other = make_user("other")
        make_project(other, "Theirs")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["projects"]]
        self.assertIn("Mine", names)
        self.assertNotIn("Theirs", names)

    def test_create_project(self):
        response = self.client.post(self.url, {"name": "New Project"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Project.objects.filter(name="New Project", user=self.user).exists())

    def test_create_project_with_description(self):
        response = self.client.post(
            self.url, {"name": "Described", "description": "A desc"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        proj = Project.objects.get(name="Described")
        self.assertEqual(proj.description, "A desc")

    def test_create_project_without_name_fails(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Projects – Detail (Retrieve / Update / Destroy)
# ---------------------------------------------------------------------------

class ProjectDetailViewTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.project = make_project(self.user, "TestProject")
        self.comp = make_component(self.user, s_no="C001", name="Comp1")

    def detail_url(self, pk=None):
        pk = pk or self.project.id
        return f"/api/project/{pk}/"

    # --- RETRIEVE ---

    def test_retrieve_project(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "TestProject")
        self.assertIn("canvas_state", response.data)

    def test_retrieve_includes_canvas_items(self):
        make_canvas_item(self.project, self.comp, sequence=0)
        response = self.client.get(self.detail_url())
        self.assertEqual(len(response.data["canvas_state"]["items"]), 1)

    def test_retrieve_includes_connections(self):
        item_a = make_canvas_item(self.project, self.comp, sequence=0, x=0, y=0)
        item_b = make_canvas_item(self.project, self.comp, sequence=1, x=100, y=0)
        Connection.objects.create(
            sourceItemId=item_a, targetItemId=item_b,
            sourceGripIndex=0, targetGripIndex=1, waypoints=[]
        )
        response = self.client.get(self.detail_url())
        self.assertEqual(len(response.data["canvas_state"]["connections"]), 1)

    def test_retrieve_sequence_counter_empty_canvas(self):
        response = self.client.get(self.detail_url())
        self.assertEqual(response.data["canvas_state"]["sequence_counter"], 0)

    def test_retrieve_sequence_counter_with_items(self):
        make_canvas_item(self.project, self.comp, sequence=5)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.data["canvas_state"]["sequence_counter"], 6)

    def test_retrieve_other_user_project_returns_404(self):
        other = make_user("other")
        other_proj = make_project(other, "OtherProj")
        response = self.client.get(self.detail_url(other_proj.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_project_returns_404(self):
        response = self.client.get(self.detail_url(99999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["status"], "error")

    # --- UPDATE ---

    def test_update_project_name(self):
        response = self.client.patch(self.detail_url(), {"name": "Renamed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Renamed")

    def test_update_replaces_canvas_state(self):
        """Saving a canvas_state should wipe old items and create new ones."""
        old_item = make_canvas_item(self.project, self.comp, sequence=0)

        new_canvas = {
            "items": [
                {
                    "id": "fake-uuid-1",
                    "component_id": self.comp.id,
                    "label": "New Item",
                    "x": 5, "y": 10,
                    "width": 60, "height": 60,
                    "rotation": 0, "scaleX": 1, "scaleY": 1,
                    "sequence": 0,
                }
            ],
            "connections": [],
        }

        response = self.client.put(
            self.detail_url(),
            {"name": self.project.name, "canvas_state": new_canvas},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CanvasState.objects.filter(id=old_item.id).exists())
        self.assertEqual(CanvasState.objects.filter(project=self.project).count(), 1)

    def test_update_creates_connections_with_remapped_ids(self):
        """Connections must use newly created CanvasState IDs, not old frontend IDs."""
        canvas = {
            "items": [
                {
                    "id": "front-1",
                    "component_id": self.comp.id,
                    "label": "A", "x": 0, "y": 0,
                    "width": 50, "height": 50,
                    "rotation": 0, "scaleX": 1, "scaleY": 1,
                    "sequence": 0,
                },
                {
                    "id": "front-2",
                    "component_id": self.comp.id,
                    "label": "B", "x": 100, "y": 0,
                    "width": 50, "height": 50,
                    "rotation": 0, "scaleX": 1, "scaleY": 1,
                    "sequence": 1,
                },
            ],
            "connections": [
                {
                    "sourceItemId": "front-1",
                    "targetItemId": "front-2",
                    "sourceGripIndex": 0,
                    "targetGripIndex": 1,
                    "waypoints": [],
                }
            ],
        }

        response = self.client.put(
            self.detail_url(),
            {"name": self.project.name, "canvas_state": canvas},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Connection.objects.filter(
            sourceItemId__project=self.project
        ).count(), 1)

    def test_update_without_canvas_state_only_updates_project(self):
        make_canvas_item(self.project, self.comp, sequence=0)
        response = self.client.patch(self.detail_url(), {"name": "NoCanvas"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Canvas items should be untouched
        self.assertEqual(CanvasState.objects.filter(project=self.project).count(), 1)

    def test_update_skips_items_without_component_id(self):
        canvas = {
            "items": [{"id": "x", "label": "No comp", "x": 0, "y": 0,
                       "width": 50, "height": 50, "rotation": 0,
                       "scaleX": 1, "scaleY": 1, "sequence": 0}],
            "connections": [],
        }
        response = self.client.put(
            self.detail_url(),
            {"name": self.project.name, "canvas_state": canvas},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CanvasState.objects.filter(project=self.project).count(), 0)

    # --- DESTROY ---

    def test_destroy_project(self):
        response = self.client.delete(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertFalse(Project.objects.filter(id=self.project.id).exists())

    def test_destroy_cascades_canvas_state(self):
        make_canvas_item(self.project, self.comp, sequence=0)
        self.client.delete(self.detail_url())
        self.assertEqual(CanvasState.objects.filter(project=self.project).count(), 0)

    def test_destroy_other_user_project_returns_404(self):
        other = make_user("other2")
        other_proj = make_project(other, "OtherProj")
        response = self.client.delete(self.detail_url(other_proj.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Project.objects.filter(id=other_proj.id).exists())


# ---------------------------------------------------------------------------
# Token Refresh
# ---------------------------------------------------------------------------

class TokenRefreshViewTests(APITestCase):
    login_url = "/api/auth/login/"
    refresh_url = "/api/auth/refresh/"

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        try:
            from axes.models import AccessAttempt, AccessLog
            AccessAttempt.objects.all().delete()
            AccessLog.objects.all().delete()
        except ImportError:
            pass

    def test_refresh_returns_new_access_token(self):
        user = make_user("dave", "davepass")
        with self.settings(REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": (
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ),
            "DEFAULT_THROTTLE_CLASSES": [],
        }):
            login = self.client.post(self.login_url, {"username": "dave", "password": "davepass"})
            self.assertEqual(login.status_code, status.HTTP_200_OK)
            refresh_token = login.data["refresh"]
            response = self.client.post(self.refresh_url, {"refresh": refresh_token})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("access", response.data)

    def test_refresh_with_invalid_token(self):
        with self.settings(REST_FRAMEWORK={
            "DEFAULT_AUTHENTICATION_CLASSES": (
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ),
            "DEFAULT_THROTTLE_CLASSES": [],
        }):
            response = self.client.post(self.refresh_url, {"refresh": "bad.token.here"})
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)