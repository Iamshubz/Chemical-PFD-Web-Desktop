import json
from google import genai
from google.genai import types
from django.conf import settings

def generate_diagram(user_input: str) -> dict:
    """
    Takes a natural language prompt and returns a structured JSON dictionary
    representing the components and connections for a Chemical PFD.
    """
    # 1. Validate API Key
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise ValueError("LLM API key is not configured in settings/environment variables.")

    client = genai.Client(api_key=api_key)

    # 2. Strict System Prompt combining original requirements and Antigravity's instructions
    system_prompt = """
    You are an expert chemical engineering assistant. Your task is to process user descriptions 
    of chemical process flow diagrams and return a structured JSON representation.
    Extract the components and the connections between them.

    STRICT RULES:
    - Use ONLY these component types: pump, tank, valve, heat_exchanger.
    - If a user mentions a synonym (like 'exchanger'), map it to 'heat_exchanger'.

    The JSON MUST match this exact schema:
    {
      "components": [
        { "type": "pump | tank | valve | heat_exchanger", "id": "string (unique string/uuid)", "label": "string" }
      ],
      "connections": [
        { "from": "id1", "to": "id2" }
      ]
    }
    
    If the user input is completely unrelated to chemical components or process flows, return exactly this JSON:
    { "error": "Invalid input. Please describe a process flow involving components like pumps, tanks, valves, etc." }
    """

    try:
        # 3. Use gemini-1.5-pro with native JSON formatting
        # 3. Use gemini-3-flash-preview with native JSON formatting
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            # model="gemini-1.5-pro",
            contents=user_input,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json"
            )
        )
        
        # 4. Generate content
        output_text = response.text.strip()
        
        # 5. Parse and return the guaranteed JSON
        parsed_data = json.loads(output_text)
        return parsed_data

    except json.JSONDecodeError:
        raise RuntimeError("LLM returned malformed JSON.")
    except Exception as e:
        raise RuntimeError(f"LLM API Error: {str(e)}")
