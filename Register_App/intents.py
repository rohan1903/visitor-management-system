# intents.py

INTENT_MAP = {
    "navigation": ["where is", "how to go", "navigate", "direction", "location"],
    "appointments": ["appointment", "meeting", "scheduled with", "i have to meet"],
    "host_lookup": ["host", "person", "employee", "anita", "raj"],
    "wifi_info": ["wifi", "internet", "network access"],
    "facilities": ["restroom", "toilet", "canteen", "lounge", "break room"],
    "complaints": ["not working", "broken", "issue", "problem", "ac not working"],
    "company_info": ["what is cbre", "about company", "company info", "cbre details"],
    "feedback": ["feedback", "experience", "suggestion", "review"],
    "headquarters": ["headquarter", "main office", "address", "location of cbre"]
}

def detect_intent(message):
    message = message.lower()
    for intent, keywords in INTENT_MAP.items():
        if any(keyword in message for keyword in keywords):
            return intent
    return "unknown"
