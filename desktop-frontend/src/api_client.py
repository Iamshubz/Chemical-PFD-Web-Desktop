import requests
import src.app_state as app_state

DEFAULT_TIMEOUT = 5  # seconds


class ApiError(Exception):
    pass


def login(username: str, password: str):
    """
    Call Django /api/auth/login/ (JWT) and return access, refresh.
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/auth/login/"

    try:
        resp = requests.post(
            url,
            json={
                "username": username,
                "password": password,
            },
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ApiError(f"Could not reach server: {e}")

    if resp.status_code == 200:
        data = resp.json()
        if "access" not in data or "refresh" not in data:
            raise ApiError("Unexpected response from server.")
        return data["access"], data["refresh"]

    elif resp.status_code in (400, 401):
        try:
            detail = resp.json().get("detail", "Invalid credentials.")
        except Exception:
            detail = "Invalid credentials."
        raise ApiError(detail)

    else:
        raise ApiError(f"Server error: {resp.status_code}")


def register(username: str, email: str, password: str):
    """
    Call Django /api/auth/register/ and return JSON if needed.
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/auth/register/"

    try:
        resp = requests.post(
            url,
            json={
                "username": username,
                "email": email,
                "password": password,
            },
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ApiError(f"Could not reach server: {e}")

    if resp.status_code in (200, 201):
        try:
            return resp.json()
        except ValueError:
            return {}

    try:
        data = resp.json()
    except ValueError:
        data = {}

    msg = (
        data.get("detail")
        or data.get("message")
        or (str(data) if data else f"Registration failed (status {resp.status_code}).")
    )
    raise ApiError(msg)


def get_components():
    url = f"{app_state.BACKEND_BASE_URL}/api/components/"
    try:
        headers = {}
        if app_state.access_token:
            headers["Authorization"] = f"Bearer {app_state.access_token}"
        
        resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()

            if isinstance(data, dict) and "components" in data:
                return data["components"]

            if isinstance(data, list):
                return data

            print("[API WARNING] Unexpected component format:", data)
            return []

    except Exception as e:
        print(f"Failed to fetch components: {e}")
    return []


def post_component(data, files):
    """
    Upload a new component (symbol) to backend.
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/components/"

    headers = {}
    if app_state.access_token:
        headers["Authorization"] = f"Bearer {app_state.access_token}"

    try:
        response = requests.post(url, headers=headers, data=data, files=files)
        return response
    except Exception as e:
        print("[API ERROR] POST failed:", e)
        return None


def get_projects():
    """
    Fetch list of all projects
    GET /api/project/
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/project/"
    headers = {}
    
    if app_state.access_token:
        headers["Authorization"] = f"Bearer {app_state.access_token}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        
        if resp.status_code == 200:
            data = resp.json()
            # Backend returns: {"status": "success", "projects": [...]}
            if isinstance(data, dict) and "projects" in data:
                return data["projects"]
            return []
        else:
            print(f"[API ERROR] Failed to fetch projects: {resp.status_code}")
            
    except Exception as e:
        print(f"[API ERROR] Failed to fetch projects: {e}")
    
    return []


def get_project(project_id):
    """
    Fetch a single project by ID
    GET /api/project/<id>/
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/project/{project_id}/"
    headers = {}
    
    if app_state.access_token:
        headers["Authorization"] = f"Bearer {app_state.access_token}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[API ERROR] Failed to fetch project: {resp.status_code}")
            
    except Exception as e:
        print(f"[API ERROR] Failed to fetch project: {e}")
    
    return None


def create_project(name, description="", canvas_state=None):
    """
    Create a new project on the backend
    POST /api/project/
    Returns the created project data including ID
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/project/"
    headers = {}
    
    if app_state.access_token:
        headers["Authorization"] = f"Bearer {app_state.access_token}"
    
    payload = {
        "name": name,
        "description": description
    }
    
    if canvas_state is not None:
        payload["canvas_state"] = canvas_state
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
        
        if resp.status_code in (200, 201):
            data = resp.json()
            # Backend returns: {"message": "...", "project": {...}}
            return data.get("project")
        else:
            print(f"[API ERROR] Failed to create project: {resp.status_code}")
            print(f"[API ERROR] Response: {resp.text}")
            
    except Exception as e:
        print(f"[API ERROR] Failed to create project: {e}")
    
    return None


def update_project(project_id, name=None, description=None, canvas_state=None):
    """
    Update an existing project on the backend
    PUT /api/project/<id>/
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/project/{project_id}/"
    headers = {}
    
    if app_state.access_token:
        headers["Authorization"] = f"Bearer {app_state.access_token}"
    
    # Build payload with only provided fields
    payload = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if canvas_state is not None:
        payload["canvas_state"] = canvas_state
    
    try:
        resp = requests.put(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[API ERROR] Failed to update project: {resp.status_code}")
            print(f"[API ERROR] Response: {resp.text}")
            
    except Exception as e:
        print(f"[API ERROR] Failed to update project: {e}")
    
    return None


def delete_project(project_id):
    """
    Delete a project
    DELETE /api/project/<id>/
    """
    url = f"{app_state.BACKEND_BASE_URL}/api/project/{project_id}/"
    headers = {}
    
    if app_state.access_token:
        headers["Authorization"] = f"Bearer {app_state.access_token}"
    
    try:
        resp = requests.delete(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[API ERROR] Failed to delete project: {resp.status_code}")
            
    except Exception as e:
        print(f"[API ERROR] Failed to delete project: {e}")
    
    return None