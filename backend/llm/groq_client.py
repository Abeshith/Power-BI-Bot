from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)


def call_groq(prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> str:
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling Groq API: {str(e)}"


def call_groq_json(prompt: str, temperature: float = 0.3, max_tokens: int = 500) -> dict:
    import json
    response_text = call_groq(prompt, temperature, max_tokens)
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON response", "raw": response_text}
