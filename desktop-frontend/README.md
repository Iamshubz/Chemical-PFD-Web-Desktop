# Chemical-PFD Desktop Application

[![Python](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/PyQt-5.x-green.svg)](https://riverbankcomputing.com/software/pyqt/intro)

The **Desktop Frontend** for the Chemical-PFD system is a high-performance, native application built with **Python** and **PyQt5**. It provides a robust environment for creating and editing detailed Chemical Process Flow Diagrams.

---

## Features

- **Native Performance:** Optimized for smooth interaction with complex diagrams.
- **Professional UI:** Modern landing page and intuitive canvas editor.
- **Component Library:** Drag-and-drop interface for chemical engineering components.
- **Backend Integration:** Seamlessly syncs projects and authentication with the Django backend.
- **Cross-Platform:** Runs on Windows, macOS, and Linux.

---

## Setup

### 1. Prerequisites

Ensure you have Python 3.x installed on your system.

### 2. Create a Virtual Environment

Navigate to the `desktop-frontend` directory:

```bash
cd desktop-frontend
```

Create a virtual environment:

```bash
python -m venv env
```

### 3. Activate the Virtual Environment

**Windows:**

```bash
env\Scripts\activate
```

**Linux / macOS:**

```bash
source env/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Application

Ensure the **Backend API** is running (refer to `../backend/README.md`).

Start the desktop application:

```bash
python main.py
```

---

## Unit Testing

Run desktop frontend unit tests from repository root:

```bash
python -m pytest desktop-frontend/desktop-frontend-UnitTests -q
```

For detailed commands and module-level coverage, see:

- `desktop-frontend/desktop-frontend-UnitTests/README.md`

---

## Project Structure

- **`main.py`**: Entry point of the application.
- **`src/`**: Core application logic (screens, navigation, API client, canvas).
- **`ui/`**: UI assets, `.ui` files (Qt Designer), and stylesheets (`.qss`).
- **`tests/`**: Unit and integration tests.

---

## Development

This application uses `PyQt5` for the GUI. UI files in `ui/` can be edited using **Qt Designer**.
