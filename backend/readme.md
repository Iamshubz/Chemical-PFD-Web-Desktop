# Django API Project

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.x-red.svg)](https://www.django-rest-framework.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

Backend API for a **Chemical Process Flow Diagram (PFD)** system built with **Django + Django REST Framework**, featuring **JWT authentication**, **project CRUD**, and **component management**.

---

## Table of Contents

- [Django API Project](#django-api-project)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration](#environment-configuration)
  - [Setup](#setup)
  - [Running the Project](#running-the-project)
  - [Running Tests](#running-tests)
  - [Authentication](#authentication)
  - [API Documentation](#api-documentation)
    - [1. Hello World](#1-hello-world)
    - [2. Authentication Endpoints](#2-authentication-endpoints)
      - [2.1 Register User](#21-register-user)
      - [2.2 Login User](#22-login-user)
      - [2.3 Refresh Access Token](#23-refresh-access-token)
    - [3. Components API](#3-components-api)
      - [3.1 List \& Create Components](#31-list--create-components)
    - [4. Projects API](#4-projects-api)
      - [4.1 List \& Create Projects](#41-list--create-projects)
      - [4.2 Project Detail \& Update \& Delete](#42-project-detail--update--delete)
  - [Admin Component Import](#admin-component-import)
  - [Authentication Flow Summary](#authentication-flow-summary)

---

## Features

- JWT Authentication (register, login, refresh)
- RESTful API using Django REST Framework
- CRUD for Projects with nested ProjectComponents
- List, fetch, and create Components
- Bulk component import via Django Admin (ZIP upload)
- SVG & PNG media support
- Test coverage for admin utilities and APIs

---

## Prerequisites

Make sure you have the following installed before getting started:

- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) — required for the recommended setup
  > 📥 **Download Docker Desktop here: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)**  
  > Docker Desktop includes both Docker and Docker Compose. Install this **before** proceeding with the PostgreSQL setup.
- [Python 3.11+](https://www.python.org/downloads/) — only required if running without Docker
- [Git](https://git-scm.com/)

---

## Environment Configuration

The project uses a `.env` file to manage environment variables such as database credentials, secret keys, and debug settings.

### 1. Create the `.env` file

Place the `.env` file in the **root of the backend project** (same directory as `manage.py` and `docker-compose.yml`):

```
backend/
├── manage.py
├── docker-compose.yml
├── .env               <-- your .env file goes here
├── requirements.txt
└── ...
```

```bash
cp .env.example .env
```

### 2. Fill in the values

Open `.env` and update the values to match your environment:

```env
DEBUG=True

POSTGRES_DB=your_local_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
SECRET_KEY=your-secret-key-here

# Superuser credentials (auto-created on first run)
SU_EMAIL=admin@example.com
SU_PASSWORD=StrongPassword123
SU_USERNAME=admin
```

| Variable | Description |
|---|---|
| `DEBUG` | Set to `True` for development, `False` for production |
| `POSTGRES_DB` | Name of the PostgreSQL database |
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `SECRET_KEY` | Django secret key — keep this private and unique |
| `SU_EMAIL` | Email for the auto-created Django superuser |
| `SU_PASSWORD` | Password for the auto-created Django superuser |
| `SU_USERNAME` | Username for the auto-created Django superuser |

> ⚠️ **Never commit your `.env` file to version control.** It is already included in `.gitignore`.  
> ⚠️ **Change the default `SECRET_KEY`** before deploying to production.

---

## Setup

Docker is used **only to run the PostgreSQL database**. Django runs locally on your machine.

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <project-folder>
```

### 2. Configure your `.env` file

Follow the [Environment Configuration](#environment-configuration) steps above.

### 3. Start the PostgreSQL container

> ⚠️ **Make sure Docker Desktop is running** before executing this command.

```bash
docker-compose up -d
```

This pulls and starts a **PostgreSQL** container in the background. Django is **not** containerized — it runs locally.

### Stopping the database container

```bash
docker-compose down
```

To also remove the database volume (wipes all data):

```bash
docker-compose down -v
```

---

### 4. Create a virtual environment

```bash
python -m venv env
```

### 5. Activate the virtual environment

**Windows**

```bash
env\Scripts\activate
```

**Linux / macOS**

```bash
source env/bin/activate
```

### 6. Install dependencies

```bash
pip install -r requirements.txt
```

### 7. Run migrations

```bash
python manage.py migrate
```

### 8. Create a superuser (required for admin)

```bash
python manage.py createsuperuser
```

---

## Running the Project

```bash
python manage.py runserver
```

Access the API at:

```
http://127.0.0.1:8000/api/
```

---

## Running Tests

Make sure your virtual environment is activated and the PostgreSQL container is running before executing the tests.

### 1. Activate the virtual environment

**Windows**

```bash
env\Scripts\activate
```

**Linux / macOS**

```bash
source env/bin/activate
```

### 2. Run the test suite

```bash
python manage.py test tests.tests --verbosity=2
```

The `--verbosity=2` flag prints the pass/fail status of each individual test as it runs:

```
test_create_component (tests.tests.ComponentListViewTests) ... ok
test_create_requires_auth (tests.tests.ComponentListViewTests) ... ok
test_login_returns_tokens (tests.tests.LoginViewTests) ... ok
test_register_success (tests.tests.RegisterViewTests) ... ok
...
----------------------------------------------------------------------
Ran 42 tests in 9.957s
OK
```

---

## Authentication

This project uses **JWT authentication**.

Include the access token in request headers:

```
Authorization: Bearer <access_token>
```

---

## API Documentation

### 1. Hello World

**Endpoint:** `/api/hello/`  
**Method:** `GET`  

**Description:** Test endpoint to check if API is working.

**Response Example:**

```json
{
  "message": "Hello from DRF!"
}
```

---

### 2. Authentication Endpoints

#### 2.1 Register User

**Endpoint:** `/api/auth/register/`  
**Method:** `POST`  

**Request Body:**

```json
{
  "username": "your_username",
  "email": "your_email@example.com",
  "password": "your_password"
}
```

**Response Example:**

```json
{
  "message": "User registered successfully",
  "user": {
    "id": 3,
    "username": "your_username",
    "email": "your_email@example.com"
  }
}
```

**Status Code:** `201 Created`

---

#### 2.2 Login User

**Endpoint:** `/api/auth/login/`  
**Method:** `POST`  

**Request Body:**

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response Example:**

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

**Status Code:** `200 OK`

---

#### 2.3 Refresh Access Token

**Endpoint:** `/api/auth/refresh/`  
**Method:** `POST`  

**Request Body:**

```json
{
  "refresh": "<refresh_token>"
}
```

**Response Example:**

```json
{
  "access": "<new_access_token>"
}
```

**Status Code:** `200 OK`

---

### 3. Components API

#### 3.1 List & Create Components

**Endpoint:** `/api/components/`  
**Method:** `GET` / `POST`  

**GET Response Example:**

```json
{
  "components": [
    {
      "id": 1,
      "s_no": "101",
      "parent": "General",
      "name": "Insulation/Tracing",
      "legend": "",
      "suffix": "",
      "object": "Insulation",
      "svg": null,
      "png": null,
      "svg_url": null,
      "png_url": null,
      "grips": ""
    }
  ]
}
```

**POST Request Example:**

```json
# Form Data
{
  "s_no": "301",
  "parent": "Piping",
  "name": "Inflow Line",
  "legend": "",
  "suffix": "",
  "object": "InflowLine",
  "svg": "<file>",
  "png": "<file>",
  "grips" : ""
}
```

**POST Response Example:**

```json
{
    "id": 2,
    "s_no": "301",
    "parent": "Piping",
    "name": "Inflow Line",
    "legend": "",
    "suffix": "",
    "object": "InflowLine",
    "svg": "<file>",
    "png": "<file>"
}
```

---

### 4. Projects API

#### 4.1 List & Create Projects

**Endpoint:** `/api/project/`  
**Method:** `GET` / `POST`  

**GET Response Example:**

```json
{
  "status": "success",
  "projects": [
    {
      "id": 1,
      "name": "Project A",
      "description": "Test project"
    }
  ]
}
```

**POST Request Example:**

```json
{
  "name": "Project B",
  "description" : "Test Project"
}
```

**POST Response Example:**

```json
{
    "message": "Project created",
    "project": {
        "id": 1,
        "name": "demo project",
        "description": "Project description",
        "created_at": "2025-12-29T14:04:51.320947Z",
        "updated_at": "2025-12-29T14:04:51.320987Z",
        "thumbnail": null,
        "user": 2
    }
}
```

---

#### 4.2 Project Detail & Update & Delete

**Endpoint:** `/api/project/<id>/`  
**Method:** `GET` / `PUT` / `DELETE`

**GET Response Example:**

```json
{
    "id": 1,
    "name": "Demo Project Updated",
    "description": "This is an updated project description for testing.",
    "created_at": "2025-12-29T14:04:51.320947Z",
    "updated_at": "2025-12-29T14:48:49.595396Z",
    "thumbnail": null,
    "user": 2,
    "status": "success",
    "canvas_state": {
        "items": [
            {
                "id": 1,
                "project": 1,
                "component_id": 101,
                "label": "Pump #1",
                "x": 100.0,
                "y": 150.0,
                "width": 50.0,
                "height": 50.0,
                "rotation": 0.0,
                "scaleX": 1.0,
                "scaleY": 1.0,
                "sequence": 1,
                "s_no": "615",
                "parent": "Instrumentation Symbol",
                "name": "Gas Filter",
                "svg": null,
                "png": null,
                "object": "GasFilter",
                "legend": "",
                "suffix": "",
                "grips": []
            },
            {
                "id": 2,
                "project": 1,
                "component_id": 102,
                "label": "Valve #1",
                "x": 300.0,
                "y": 150.0,
                "width": 50.0,
                "height": 50.0,
                "rotation": 0.0,
                "scaleX": 1.0,
                "scaleY": 1.0,
                "sequence": 2,
                "s_no": "616",
                "parent": "Instrumentation Symbol",
                "name": "Interlock",
                "svg": null,
                "png": null,
                "object": "Interlock",
                "legend": "",
                "suffix": "",
                "grips": []
            }
        ],
        "connections": [
            {
                "id": 1,
                "sourceItemId": 1,
                "sourceGripIndex": 0,
                "targetItemId": 2,
                "targetGripIndex": 1,
                "waypoints": [
                    {"x": 150, "y": 150},
                    {"x": 250, "y": 150}
                ]
            }
        ],
        "sequence_counter": 3.0
    }
}
```

**PUT Request Example (Update Components):**

```json
{
  "id": 1,
  "name": "Demo Project Updated",
  "description": "This is an updated project description for testing.",
  "created_at": "2025-12-29T14:04:51.320947Z",
  "updated_at": "2025-12-29T14:45:21.523416Z",
  "thumbnail": null,
  "user": 2,
  "status": "success",
  "canvas_state": {
    "items": [
      {
        "id": 1,
        "component": {"id": 101, "name": "Pump"},
        "label": "Pump #1",
        "x": 100, "y": 150,
        "width": 50, "height": 50,
        "rotation": 0, "scaleX": 1, "scaleY": 1,
        "sequence": 1,
        "connections": []
      },
      {
        "id": 2,
        "component": {"id": 102, "name": "Valve"},
        "label": "Valve #1",
        "x": 300, "y": 150,
        "width": 50, "height": 50,
        "rotation": 0, "scaleX": 1, "scaleY": 1,
        "sequence": 2,
        "connections": []
      }
    ],
    "connections": [
      {
        "id": 1,
        "sourceItemId": 1,
        "sourceGripIndex": 0,
        "targetItemId": 2,
        "targetGripIndex": 1,
        "waypoints": [
          {"x": 150, "y": 150},
          {"x": 250, "y": 150}
        ]
      }
    ],
    "sequence_counter": 3
  }
}
```

**PUT Response Example:**

```json
{
    "id": 1,
    "name": "Demo Project Updated",
    "description": "This is an updated project description for testing.",
    "created_at": "2025-12-29T14:04:51.320947Z",
    "updated_at": "2025-12-29T14:55:34.762297Z",
    "thumbnail": null,
    "user": 2,
    "status": "success",
    "canvas_state": {
        "items": [
            {
                "id": 1,
                "project": 1,
                "component_id": 101,
                "label": "Pump #1",
                "x": 100.0, "y": 150.0,
                "width": 50.0, "height": 50.0,
                "rotation": 0.0, "scaleX": 1.0, "scaleY": 1.0,
                "sequence": 1,
                "s_no": "615",
                "parent": "Instrumentation Symbol",
                "name": "Gas Filter",
                "svg": null, "png": null,
                "object": "GasFilter",
                "legend": "", "suffix": "",
                "grips": []
            },
            {
                "id": 2,
                "project": 1,
                "component_id": 102,
                "label": "Valve #1",
                "x": 300.0, "y": 150.0,
                "width": 50.0, "height": 50.0,
                "rotation": 0.0, "scaleX": 1.0, "scaleY": 1.0,
                "sequence": 2,
                "s_no": "616",
                "parent": "Instrumentation Symbol",
                "name": "Interlock",
                "svg": null, "png": null,
                "object": "Interlock",
                "legend": "", "suffix": "",
                "grips": []
            }
        ],
        "connections": [
            {
                "id": 1,
                "sourceItemId": 1,
                "sourceGripIndex": 0,
                "targetItemId": 2,
                "targetGripIndex": 1,
                "waypoints": [
                    {"x": 150, "y": 150},
                    {"x": 250, "y": 150}
                ]
            }
        ],
        "sequence_counter": 3.0
    }
}
```

**DELETE Response Example:**

```json
{
    "status": "success",
    "message": "Project deleted successfully"
}
```

**Not Found Response Example:**

```json
{
    "status": "error",
    "message": "Project not found"
}
```

---

## Admin Component Import

Components can be bulk imported via Django Admin using a ZIP file.

**ZIP structure:**

```
components/
├── components.csv
├── svg/
│   ├── component_1.svg
│   └── component_2.svg
└── png/
    ├── component_1.png
    └── component_2.png
```

1. Login to Django Admin (`/admin/`)  
2. Go to **Components** → **Upload ZIP**  
3. Upload the ZIP following the structure above  

---

## Authentication Flow Summary

1. **Register** → create user  
2. **Login** → receive access & refresh tokens  
3. **Access protected endpoints** → include `Authorization: Bearer <access>` header  
4. **Refresh** → get new access token using refresh token  
