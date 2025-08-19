import os, re, json
import requests
from flask import Flask, request, abort

app = Flask(__name__)

# --- REQUIRED SECRETS / IDs (fill these!) ---
TELEGRAM_BOT_TOKEN = "8394102086:AAHnV5Fg8DUS4rz2rzrXD3zVHuBIQ3ri4II"
VAPI_API_KEY         = os.getenv("VAPI_API_KEY", "9cbbc767-37eb-4eef-aca3-7ec71519496d")
VAPI_ASSISTANT_ID    = os.getenv("VAPI_ASSISTANT_ID", "ade2369f-5cac-44e9-bd99-d764d0d8ba0c")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "cd6a4034-1f8f-478a-bfe0-86f1c8f33b93")  # your Vapi number

# --- OPTIONAL: set these at runtime when you start cloudflared ---
PUBLIC_BASE_URL = "https://requests-mandate-wishing-marking.trycloudflare.com"  # no trailing slash
TELEGRAM_WEBHOOK_PATH = "/webhook"
VAPI_WEBHOOK_PATH     = "/vapi"

# --- Telegram helpers ---
def tg_api(method: str):
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"

def tg_send(chat_id, text):
    try:
        requests.post(tg_api("sendMessage"), data={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram send error:", e)

def set_telegram_webhook():
    url = f"{PUBLIC_BASE_URL}{TELEGRAM_WEBHOOK_PATH}"
    r = requests.post(tg_api("setWebhook"), data={"url": url}, timeout=10)
    print("SetWebhook response:", r.status_code, r.text)

# --- Vapi: create outbound PHONE call ---
def vapi_create_call(target_number: str, chat_id: int):
    """
    Creates an outbound phone call via Vapi and attaches chat_id in metadata
    so we can route Vapi events back to the right Telegram chat.
    """
    endpoint = "https://api.vapi.ai/call/phone"  # public Postman collection shows this endpoint
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
    "assistant": {
        "firstName": "TestBot"   # ✅ instead of assistantId
    },
    "customer": {
        "number": target_number  # ✅ must look like +18761234567
    },
    "metadata": {
        "chat_id": chat_id,
        "intent": "collect_age"
    }
}
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=20)
        print("Vapi create call:", resp.status_code, resp.text)
        if resp.ok:
            data = resp.json()
            call_id = data.get("id") or data.get("call", {}).get("id")
            return True, call_id
        return False, None
    except Exception as e:
        print("Vapi create error:", e)
        return False, None

# --- Extract an age (very simple heuristic) ---
AGE_RE = re.compile(r"(?:\bage\b\s*(?:is|=|:)?\s*|I\s*am\s*|I'm\s*)(\d{1,3})", re.IGNORECASE)
FALLBACK_NUMBER_RE = re.compile(r"\b(1[01][0-9]|1[2-4][0-9]|[6-9]?[0-9]|12[0])\b")  # 0-120

def extract_age(text: str):
    if not text:
        return None
    m = AGE_RE.search(text)
    if m:
        n = int(m.group(1))
        if 0 < n <= 120:
            return n
    # fallback: first plausible number 0-120
    for m in FALLBACK_NUMBER_RE.finditer(text):
        n = int(m.group(0))
        if 0 < n <= 120:
            return n
    return None

# --- Telegram webhook ---
@app.route(TELEGRAM_WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    update = request.get_json(force=True, silent=True) or {}
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return "OK", 200

    if text.lower().startswith("/call"):
        # Expect: /call +15551234567
        parts = text.split()
        if len(parts) < 2:
            tg_send(chat_id, "Usage: /call +15551234567")
            return "OK", 200
        to_number = parts[1]
        tg_send(chat_id, f"📞 Calling {to_number} to ask for age...")
        ok, call_id = vapi_create_call(to_number, chat_id)
        if ok:
            tg_send(chat_id, f"✅ Call started (id: {call_id or 'unknown'}). I’ll post the result here.")
        else:
            tg_send(chat_id, "❌ Could not start the call. Check your Vapi keys/ids and balance.")
        return "OK", 200

    tg_send(chat_id, "Send /call +15551234567 to start a voice call that asks for age.")
    return "OK", 200

# --- Vapi server/webhook endpoint ---
@app.route(VAPI_WEBHOOK_PATH, methods=["POST"])
def vapi_webhook():
    """
    Vapi sends many event types to the 'Server URL':
      - status updates, transcript updates, function calls, end-of-call report, etc.
    We’ll try to pull chat_id from call.metadata and parse transcripts to find an age.
    """
    data = request.get_json(force=True, silent=True) or {}
    # Log raw for debugging
    print("Vapi event:", json.dumps(data)[:2000])

    message = data.get("message") or {}
    call = message.get("call") or {}
    metadata = call.get("metadata") or {}
    chat_id = metadata.get("chat_id")

    # Try to collect text from different possible shapes
    text_chunks = []

    # 1) transcript style events (common)
    if message.get("type", "").startswith("transcript"):
        # Some payloads carry 'text' or 'delta'
        t = message.get("text") or message.get("delta") or ""
        text_chunks.append(t)

    # 2) end-of-call report often carries summary and/or transcripts
    report = message.get("report") or {}
    if isinstance(report, dict):
        # Try common fields we’ve seen
        for key in ("transcript", "summary", "customerTranscript", "assistantTranscript"):
            val = report.get(key)
            if isinstance(val, str):
                text_chunks.append(val)

    # 3) sometimes the transcript array sits on call
    if isinstance(call.get("transcripts"), list):
        for item in call["transcripts"]:
            if isinstance(item, dict):
                t = item.get("text") or item.get("transcript")
                if t:
                    text_chunks.append(t)

    collected_text = "\n".join(filter(None, text_chunks)).strip()

    if collected_text:
        age = extract_age(collected_text)
        if age is not None and chat_id:
            tg_send(chat_id, f"🎉 Age captured from call: {age}")
            return "OK", 200

    # Also handle explicit end-of-call so the user isn’t left hanging
    if message.get("type") in ("end-of-call-report", "status-update"):
        # If we reached end and still no age but we know the chat, let them know
        status = message.get("status") or call.get("status")
        if chat_id and status in (None, "completed", "ended", "no-answer", "failed"):
            if collected_text:
                tg_send(chat_id, "ℹ️ Call ended. I couldn’t find a clear age in the transcript.")
            else:
                tg_send(chat_id, "ℹ️ Call ended. No transcript received yet.")
    return "OK", 200

# --- Local run ---
if __name__ == "__main__":
    # Set Telegram webhook to our Cloudflare tunnel URL
    try:
        set_telegram_webhook()
    except Exception as e:
        print("Webhook set failed (you can set it later):", e)
    app.run(host="0.0.0.0", port=5000)
