# AI Diagram Generation Testing Guide

This document provides instructions on how to set up and test the new `/api/ai-generate/` feature in the backend. 

## 1. Setup & Configuration

Before testing the endpoint, ensure your local environment is correctly configured with the new Gemini SDK.

1. **Environment Variables**: Open your `backend/.env` file and verify your Gemini API key is set:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
2. **Dependencies**: Make sure you have installed the updated dependencies. We recently migrated to the unified `google-genai` SDK. Ensure your virtual environment (`env`) is active, then run:
   ```bash
   pip install -r requirements.txt
   ```
3. **Database & Server**: 
   - Start **Docker Desktop** (wait for it to fully load).
   - In the `backend` directory, start the Postgres database: `docker-compose up -d`
   - Start the Django server: `python manage.py runserver`

---

## 2. Testing the Endpoint

The endpoint is located at `POST http://127.0.0.1:8000/api/ai-generate/`. 
*Note: For testing convenience, we have set this endpoint to `@permission_classes([AllowAny])` so you do not need Bearer token authentication.*

### Option A: Using Postman
1. Open Postman and create a new request.
2. Set the Method to **POST**.
3. Set the URL to `http://127.0.0.1:8000/api/ai-generate/`
4. Go to the **Body** tab, select **raw**, and change the dropdown from `Text` to **`JSON`**.
5. Paste the following test payload:
   ```json
   {
     "prompt": "We have a chemical cycle. It starts with a tank that is connected to a heavy duty pump. The pump then pushes the liquid into a heat exchanger, and the exchanger is connected to a final valve."
   }
   ```
6. Click **Send**.

### Option B: Using cURL
If you prefer the terminal, you can test it with the following command:

**macOS/Linux:**
```bash
curl -X POST http://127.0.0.1:8000/api/ai-generate/ \
-H "Content-Type: application/json" \
-d '{"prompt": "A tank connected to a pump, which is then connected to a valve"}'
```

**Windows (PowerShell):**
```powershell
curl -Method POST -Uri http://127.0.0.1:8000/api/ai-generate/ `
-Headers @{"Content-Type"="application/json"} `
-Body '{"prompt": "A pump connected to a tank, which then feeds into a valve"}'
```

---

## 3. Expected Output

The endpoint uses `google.genai` under the hood (specifically `gemini-1.5-pro` with rigid structured JSON formatting). 

**Successful Generation (200 OK):**
You will receive a strictly formatted sequence of unique UI components and connections:
```json
{
  "components": [
    { "type": "tank", "id": "uuid-1234", "label": "Storage Tank" },
    { "type": "pump", "id": "uuid-5678", "label": "Heavy Pump" },
    { "type": "heat_exchanger", "id": "uuid-9012", "label": "Heat Exchanger" }
  ],
  "connections": [
    { "from": "uuid-1234", "to": "uuid-5678" },
    { "from": "uuid-5678", "to": "uuid-9012" }
  ]
}
```

**Graceful Rejection (400 Bad Request):**
If the AI detects the prompt has absolutely nothing to do with chemical components or engineering diagrams (e.g., asking for a cake recipe), it will politely reject the request in a structured format:
```json
{
    "error": "Invalid input. Please describe a process flow involving components like pumps, tanks, valves, etc."
}
```

---

## Architecture Note
The business logic for the LLM interaction resides entirely within `backend/core/gemini_service.py` (The Service Layer). The `backend/api/views.py` merely handles HTTP validation and response routing. This enables extremely clean, re-usable, and testable code within your application!
