import json
from google import genai
from google.genai import types
from django.conf import settings


def generate_diagram(user_input: str, available_components: list = None) -> dict:
    """
    Takes a natural language prompt and returns a structured JSON dictionary
    representing the components and connections for a Chemical PFD.
    """

    # 1. Validate API Key
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError("LLM API key is not configured.")

    client = genai.Client(api_key=api_key)

    # Fallback to defaults if not provided
    if not available_components:
        available_components = ["pump", "valve", "tank", "heat_exchanger", "compressor", "reactor", "separator"]

    components_str = ", ".join(available_components)

    # 2. SYSTEM PROMPT
    system_prompt = f"""
      You are a system that converts process descriptions into STRICT JSON.

      RULES:
      1. Use ONLY these component types exactly:
      {components_str}

      2. DO NOT use variations or synonyms.

      3. Generate EXACTLY the number of UNIQUE components implied by the input. If a component type is mentioned again (e.g. "tank connected back to pump"), DO NOT create a duplicate component unless explicitly requested. Reuse the existing component's ID to create a feedback loop or complex connection.

      4. Each component must have:
      - id (string, e.g. "c1", "c2"...)
      - type (string, from allowed list)
      - label (string)
      - x (integer, horizontal placement. VARY THIS.)
      - y (integer, vertical placement. CRITICAL: You MUST use 2D space. DO NOT place all components on the same Y-axis. Arrange them in a cycle, zig-zag, or branched pattern by mixing Y values like 100, 300, 500.)

      5. Connections must accurately represent the flow. Feedback loops and multiple connections to the same component are allowed.

      6. Every component must be connected. Do NOT skip components.

      7. Output STRICT JSON only.

      FORMAT:
      {{
        "components": [
          {{ "id": "c1", "type": "tank", "label": "Main Tank", "x": 100, "y": 300 }},
          {{ "id": "c2", "type": "pump", "label": "Pump", "x": 300, "y": 100 }}
        ],
        "connections": [
          {{ "from": "c1", "to": "c2" }}
        ]
      }}

      ERROR:
      If invalid input:
      {{ "error": "Invalid process description" }}
    """

    try:
        # 3. Generate structured JSON response
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                temperature=0.3  # 🔥 more consistent output
            )
        )

        output_text = response.text.strip()

        # 4. Parse JSON safely
        parsed_data = json.loads(output_text)

        if "error" in parsed_data:
            return parsed_data

        # 5. VALIDATION
        if "components" not in parsed_data or "connections" not in parsed_data:
            raise ValueError("Invalid AI response structure")

        component_ids = {c.get("id") for c in parsed_data.get("components", []) if c.get("id")}
        
        for comp in parsed_data["components"]:
            if "id" not in comp or "type" not in comp:
                raise ValueError("Invalid component format")
                
        for conn in parsed_data["connections"]:
            if conn.get("from") not in component_ids or conn.get("to") not in component_ids:
                raise ValueError("Invalid connection reference")

        return parsed_data

    except json.JSONDecodeError:
        raise RuntimeError("LLM returned malformed JSON")

    except Exception as e:
        return {
            "error": str(e)
        }