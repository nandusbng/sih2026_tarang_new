import requests

GEMINI_API_KEY = "YOUR_API_KEY_HERE"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

payload = {
    "contents": [{"parts": [{"text": "hi"}]}],
    "systemInstruction": {
        "parts": [
            {"text": "You are TARANG AI, an assistant for the TARANG Marine Intelligence Platform. Answer questions related to this platform, underwater sonar, hotspot detection, and cleanup missions. Keep your answers concise, helpful, and focused strictly on the website concept. IMPORTANT: You must respond entirely in Hindi."}
        ]
    }
}

resp = requests.post(url, json=payload)
print("Status:", resp.status_code)
print("Response:", resp.json())
