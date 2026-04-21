import json
from google import genai
from google.genai import types
from django.conf import settings


def generate_diagram(user_input: str) -> dict:
    """
    Takes a natural language prompt and returns a structured JSON dictionary
    representing the components and connections for a Chemical PFD.
    """

    # ✅ 1. Validate API Key
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError("LLM API key is not configured.")

    client = genai.Client(api_key=api_key)

    # ✅ 2. IMPROVED SYSTEM PROMPT (CRITICAL FIX)
    system_prompt = """
    You are an expert chemical engineering assistant.

    Your task is to convert a user’s process description into a structured
    process flow diagram JSON.

    -------------------------
    RULES (VERY IMPORTANT)
    -------------------------

    1. Use realistic industrial components such as:
       - Pumps (centrifugal pump, reciprocating pump)
       - Compressors (centrifugal compressor, reciprocating compressor)
       - Valves (gate valve, globe valve, control valve)
       - Tanks / vessels (storage tank, vertical vessel, horizontal vessel)
       - Heat exchangers
       - Dryers
       - Separators
       - Reactors

    2. ALWAYS generate a VARIETY of components.
       ❌ Do NOT repeat the same type unnecessarily.

    3. If multiple components exist:
       ✅ ALL must be connected in a proper sequence
       Example: c1 → c2 → c3 → c4

    4. Generate at least 4–6 components if possible.

    5. Each component MUST have:
       - unique id (c1, c2, c3…)
       - type (specific, not generic like "pump" → use "centrifugal pump")
       - label (human readable)

    -------------------------
    OUTPUT FORMAT (STRICT JSON ONLY)
    -------------------------

   {
  "components": [
    {
      "id": "c1",
      "type": "pump",
      "variant": "centrifugal pump",
      "label": "Pump 1"
    },
    {
      "id": "c2",
      "type": "heat_exchanger",
      "variant": "shell and tube heat exchanger",
      "label": "Heat Exchanger"
    }
  ],
  "connections": [
    { "from": "c1", "to": "c2" }
  ]
}

    -------------------------
    ERROR CASE
    -------------------------

    If the input is unrelated to process systems, return:

    { "error": "Invalid input. Please describe a process flow involving industrial components." }
    """

    try:
        # ✅ 3. Generate structured JSON response
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

        # ✅ 4. Parse JSON safely
        parsed_data = json.loads(output_text)

        # ✅ 5. VALIDATION (IMPORTANT FIX)
        if "components" not in parsed_data or "connections" not in parsed_data:
            raise ValueError("Invalid AI response structure")

        return parsed_data

    except json.JSONDecodeError:
        raise RuntimeError("LLM returned malformed JSON")

    except Exception as e:
        return {
            "error": str(e)
        }