"""
Local web interface for the Madhan Support Agent.

Run with:
    D:\\madhan\\project\\maddy\\venv\\Scripts\\python.exe -m uvicorn app:app --reload

Then open http://127.0.0.1:8000 in your browser.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import AGENT_NAME, OWNER_NAME
from src.agent import run_agent, init

app = FastAPI(title=AGENT_NAME)

_session_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    escalated: bool
    needs_human: bool
    confidence: str
    fact_learned: Optional[str] = None
    preference_learned: Optional[str] = None
    reminder_set: Optional[str] = None
    session_id: str


@app.on_event("startup")
def _startup():
    global _session_id
    import uuid
    _session_id = str(uuid.uuid4())[:8]
    try:
        count = init()
    except Exception as e:  # noqa: BLE001
        print("[app] knowledge-base init failed:", e)
        count = 0
    print(f"[app] session={_session_id} | docs embedded={count}")


@app.get("/health")
def health():
    return {"status": "ok", "agent": AGENT_NAME, "owner": OWNER_NAME}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    global _session_id
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    if _session_id is None:
        import uuid
        _session_id = str(uuid.uuid4())[:8]
    out = run_agent(session_id=_session_id, user_input=req.message)
    return ChatResponse(
        answer=out.get("answer", ""),
        sources=out.get("sources", []),
        escalated=bool(out.get("escalated")),
        needs_human=bool(out.get("needs_human")),
        confidence=out.get("confidence", "medium"),
        fact_learned=out.get("fact_learned"),
        preference_learned=out.get("preference_learned"),
        reminder_set=out.get("reminder_set"),
        session_id=_session_id,
    )


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_PAGE)


_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Madhan Support Agent</title>
<style>
  :root { --bg:#0f1220; --panel:#171b2e; --accent:#6c8cff; --ok:#38d39f; --warn:#ffcf5c; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:Segoe UI, Roboto, sans-serif; background:var(--bg); color:#e6e9f5; height:100vh; display:flex; flex-direction:column; }
  header { padding:14px 22px; background:var(--panel); border-bottom:1px solid #2a3152; display:flex; align-items:center; gap:12px; }
  header h1 { font-size:18px; margin:0; background:linear-gradient(90deg,#6c8cff,#b06cff); -webkit-background-clip:text; background-clip:text; color:transparent; }
  header .badge { font-size:11px; color:#9aa3c7; }
  #chat { flex:1; overflow-y:auto; padding:20px 24px; display:flex; flex-direction:column; gap:14px; }
  .msg { max-width:76%; padding:12px 16px; border-radius:14px; white-space:pre-wrap; line-height:1.5; }
  .user { align-self:flex-end; background:var(--accent); color:#0f1220; }
  .agent { align-self:flex-start; background:var(--panel); border:1px solid #2a3152; }
  .meta { font-size:11px; color:#8a93bd; margin-top:8px; }
  .meta .warn { color:var(--warn); }
  .meta .ok { color:var(--ok); }
  footer { display:flex; gap:10px; padding:14px 20px; background:var(--panel); border-top:1px solid #2a3152; }
  input { flex:1; padding:12px 14px; border-radius:10px; border:1px solid #2a3152; background:#0f1220; color:#e6e9f5; font-size:15px; }
  button { padding:12px 20px; border:none; border-radius:10px; background:var(--accent); color:#0f1220; font-weight:700; cursor:pointer; }
  button:disabled { opacity:.5; }
  #status { font-size:12px; color:#8a93bd; }
</style>
</head>
<body>
<header>
  <h1>Madhan Support Agent</h1>
  <span class="badge">hybrid search · memory · guardrails</span>
</header>
<main id="chat"><div class="msg agent">Hi Madhan! Ask me anything about your knowledge base.</div></main>
<footer>
  <input id="input" placeholder="Type your question..." autofocus>
  <button id="send">Send</button>
  <span id="status"></span>
</footer>
<script>
const chat = document.getElementById('chat'), inp = document.getElementById('input'),
      btn = document.getElementById('send'), st = document.getElementById('status');
function add(text, cls){ const d=document.createElement('div'); d.className='msg '+cls; d.textContent=text; chat.appendChild(d); chat.scrollTop=chat.scrollHeight; return d; }
async function send(){
  const m = inp.value.trim(); if(!m) return;
  inp.value=''; btn.disabled=true; st.textContent='thinking...';
  add(m,'user');
  try{
    const r = await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m})});
    const data = await r.json();
    let el = add(data.answer,'agent');
    const parts=[];
    if(data.sources && data.sources.length) parts.push('sources: '+data.sources.join(', '));
    if(data.escalated) parts.push('!! ESCALATED to Madhan');
    if(data.needs_human) parts.push('! flagged for Madhan');
    if(data.confidence) parts.push('confidence: '+data.confidence);
    if(parts.length){ const sm=document.createElement('div'); sm.className='meta';
      sm.innerHTML=parts.map(p=>p.startsWith('!!')||p.startsWith('!')?`<span class="warn">${p}</span>`:`<span class="ok">${p}</span>`).join(' · '); el.appendChild(sm); }
  }catch(e){ add('Error: '+e.message,'agent'); }
  finally{ btn.disabled=false; st.textContent=''; inp.focus(); }
}
btn.onclick=send; inp.addEventListener('keydown',e=>{ if(e.key==='Enter') send(); });
</script>
</body>
</html>
"""
