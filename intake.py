#!/usr/bin/env python3
"""Job-intake assistant for a small electrical business.
Runs an open-weight model locally through Ollama. No internet, no API key,
customer details never leave this computer. Python standard library only.

Usage:  python intake.py            (paste a customer message, press Enter twice)
Model:  MODEL=qwen2.5:3b python intake.py
Low-data option (llama.cpp server on port 8080):
        OLLAMA_URL=http://localhost:8080/v1/chat/completions python intake.py

Design: the small model reads the messy message and writes the summary (and
classifies anything the rules don't recognise). Safety, urgency, follow-up
questions and pricing rules are plain code, so they never depend on the model.
"""
import json, os, re, urllib.request

MODEL = os.environ.get("MODEL", "llama3.2:3b")
URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

# (service, keyword regexes). Checked in order; several services can match.
RULES = [
    ("ATS (automatic transfer switch)", [r"\bats\b", r"transfer switch", r"changeover"]),
    ("Contactors and components", [r"\bcontactor", r"\brelay", r"\bcomponent"]),
    ("Pump or motor rewinding", [r"\bcoil", r"\brewind", r"\bpump", r"\bmotor"]),
    ("Solar installation", [r"\bsolar", r"\binverter"]),
    ("CCTV", [r"\bcctv", r"\bcamera"]),
    ("Burnt or damaged wiring", [r"\bburn", r"\bdamage"]),
    ("Switch or socket fault", [r"\bswitch", r"\bsocket"]),
    ("House wiring", [r"\bwiring", r"\bwire", r"\bbedroom", r"\brewire"]),
    ("Urgent equipment repair", [r"\biron\b", r"\bgrind", r"\bblender", r"\bheater", r"\bappliance"]),
]
QUESTIONS = {
    "ATS (automatic transfer switch)": ["What amperage do you need (100A or higher)?",
        "Regular or premium quality?", "Single-phase or three-phase?"],
    "Contactors and components": ["What is the rating (amps) and coil voltage, or can you send a photo of the old one?",
        "How many do you need?"],
    "Pump or motor rewinding": ["What is the pump or motor rating (HP or kW) and brand?",
        "Can you send a photo, or bring the machine for inspection?"],
    "Solar installation": ["Is it for a home or a business?", "What do you want to power (lights, fridge, AC)?"],
    "CCTV": ["How many cameras do you need?", "Indoor or outdoor cameras?"],
    "Burnt or damaged wiring": ["Which room or area is affected?", "Can you send a photo, only if it is safe?"],
    "Switch or socket fault": ["Which switch or socket is it?", "What is happening (no power, tripping, hot)?"],
    "House wiring": ["How many bedrooms, and is it new wiring or a rewire?"],
    "Urgent equipment repair": ["What equipment is it and what is it doing?",
        "Can you bring it in, or must we come to you?"],
    "OTHER": ["Please describe the problem."],
}
SERVICES = [s for s, _ in RULES] + ["OTHER"]

DANGER = [r"\bburn", r"\bsmoke", r"\bspark", r"\bshock", r"\bfire", r"electrocut",
          r"\bmelt", r"overheat", r"hot wire", r"\bsmell", r"explod"]
URGENT = [r"\burgent", r"\bemergency", r"\bimmediate", r"\basap\b", r"right now"]
PRICE = [r"how much", r"\bprice", r"\bcost", r"\bquote", r"\bpremium", r"\bregular"]
PRICE_LINE = " The owner will confirm the exact price after seeing the job or the exact part."
SAFETY_LINE = (" If it is safe to do so, please switch off at the main breaker and keep"
               " away from the area until we reach you.")

SCHEMA = {"type": "object", "properties": {
    "service": {"type": "string", "enum": SERVICES},
    "summary": {"type": "string"}}, "required": ["service", "summary"]}
SYSTEM = """You help a small electrical business. Customers may write in simple English or Pidgin.
Return the service type and ONE short sentence summary for the owner, starting with "Customer says".
Use only facts in the message. Never add addresses, prices, names or promises."""

def has(patterns, text):
    return any(re.search(p, text) for p in patterns)

def ask(message):
    body = {"model": MODEL, "stream": False, "options": {"temperature": 0.1},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": message}]}
    if "/v1/" in URL:
        body["response_format"] = {"type": "json_object"}
    else:
        body["format"] = SCHEMA
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.load(r)
    text = (data["choices"][0]["message"]["content"] if "choices" in data
            else data["message"]["content"])
    return json.loads(text)

def clean_summary(summary, msg):
    """Reject model summaries that contain money or numbers the customer never wrote."""
    summary = (summary or "").strip()
    nums = lambda t: set(re.findall(r"\d+", t))
    money = re.search(r"[$]|\b(naira|cedis?|ghs|usd|ngn|dollars?)\b", summary.lower())
    if not summary or money or not nums(summary) <= nums(msg):
        summary = "Customer says: " + msg[:150]
    return summary

def build(msg, model):
    low = msg.lower()
    found = [s for s, pats in RULES if has(pats, low)]
    if "ATS (automatic transfer switch)" in found and "Switch or socket fault" in found:
        found.remove("Switch or socket fault")
    if "Burnt or damaged wiring" in found and "House wiring" in found:
        found.remove("House wiring")
    if not found:  # rules don't recognise it: trust the model's classification
        found = [model.get("service") if model.get("service") in SERVICES else "OTHER"]
    found = found[:3]
    danger = has(DANGER, low)
    urgency = "EMERGENCY" if danger else "URGENT" if has(URGENT, low) else "NORMAL"
    qs = []
    for s in found:
        qs += [q for q in QUESTIONS[s] if q not in qs]
    qs = qs[:4]
    summary = clean_summary(model.get("summary"), msg)
    if has(PRICE, low):
        summary += " Customer is asking about price."
    reply = ("Hello, thank you for contacting us. To help you, please tell us: "
             + " ".join(f"({i}) {q}" for i, q in enumerate(qs, 1))
             + " The owner will review your request and reply."
             + (PRICE_LINE if has(PRICE, low) else "") + (SAFETY_LINE if danger else ""))
    return {"service": " + ".join(found), "urgency": urgency, "summary": summary,
            "questions": qs, "draft_reply": reply, "danger": danger}

def show(r):
    if r["danger"]:
        print("\n!!! SAFETY FLAG: possible fire or shock risk. Call the customer NOW.")
    print(f"\nSERVICE: {r['service']}\nURGENCY: {r['urgency']}\nSUMMARY: {r['summary']}")
    print("ASK THE CUSTOMER:")
    for q in r["questions"]:
        print(f"  - {q}")
    print(f"DRAFT REPLY: {r['draft_reply']}\n" + "-" * 50 + "\n")

def main():
    print(f"Intake assistant running locally with {MODEL}. Ctrl+C to quit.\n")
    while True:
        print("Paste customer message (blank line to finish):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        msg = " ".join(lines).strip()
        if not msg:
            continue
        try:
            model = ask(msg)
        except Exception as e:
            print(f"\nModel unavailable ({e}). Using rules only.\n")
            model = {}
        show(build(msg, model))

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")