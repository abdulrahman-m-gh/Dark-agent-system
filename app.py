
import streamlit as st
import json, time, re
import plotly.graph_objects as go
import pandas as pd
from groq import Groq
from datetime import datetime
 
st.set_page_config(page_title="DARK · Multi-Agent Decision Intelligence", page_icon="🖤", layout="wide")
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'JetBrains Mono',monospace!important;}
.stApp{background:#08090f!important;}
.command-box{background:linear-gradient(135deg,#110a1a,#1a0d2e);border:1px solid rgba(213,0,249,0.35);border-radius:12px;padding:18px 20px;color:#e2e8f0;font-size:13px;line-height:1.8;white-space:pre-wrap;}
.metric-box{background:#0c0f1a;border:1px solid #1a1f2e;border-radius:10px;padding:12px 10px;text-align:center;}
[data-testid="stMetric"]{background:#0c0f1a;border:1px solid #1a1f2e;border-radius:10px;padding:12px 14px;}
[data-testid="stMetricLabel"]{color:#4a5568!important;font-size:10px!important;letter-spacing:2px!important;}
[data-testid="stMetricValue"]{color:#e2e8f0!important;}
.stButton>button{background:linear-gradient(135deg,#0d1a2a,#001a35)!important;color:#00e5ff!important;border:1px solid rgba(0,229,255,0.3)!important;border-radius:8px!important;letter-spacing:1px!important;}
.stButton>button:hover{border-color:#00e5ff!important;}
.stButton>button:disabled{opacity:0.4!important;}
[data-testid="stSidebar"]{background:#0d1117!important;border-right:1px solid #1a1f2e;}
.stTextArea textarea{background:#0c0f1a!important;border:1px solid #1a1f2e!important;color:#e2e8f0!important;border-radius:8px!important;}
input[type="password"],input[type="text"]{background:#0c0f1a!important;border:1px solid #1a1f2e!important;color:#e2e8f0!important;border-radius:8px!important;}
.stProgress>div>div>div{background:linear-gradient(90deg,#00e5ff,#2979ff)!important;}
[data-testid="stExpander"]{background:#0c0f1a!important;border:1px solid #1a1f2e!important;border-radius:8px!important;}
hr{border-color:#1e2d3d!important;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)
 
AGENTS = [
    {"id":"scout",   "name":"SCOUT",   "role":"Signal Detection",    "icon":"◈","color":"#00e5ff"},
    {"id":"analyst", "name":"ANALYST", "role":"Deep Analysis",       "icon":"◉","color":"#2979ff"},
    {"id":"risk",    "name":"RISK",    "role":"Risk Quantification", "icon":"◬","color":"#ffab00"},
    {"id":"strategy","name":"STRATEGY","role":"Action Planning",     "icon":"◆","color":"#d500f9"},
    {"id":"command", "name":"COMMAND", "role":"Final Authority",     "icon":"★","color":"#ff1744"},
]
 
PRESETS = [
    {"id":1,"icon":"🚢","tag":"LOGISTICS","title":"Supply Chain Disruption","description":"Primary supplier in Southeast Asia halted operations due to factory flooding. 60% of Q3 inventory pipeline at risk. Alternative sourcing lead time 8-12 weeks. $4.2M in committed purchase orders exposed."},
    {"id":2,"icon":"📈","tag":"DEMAND","title":"Viral Demand Surge","description":"TikTok review generated 340% spike in product demand over 6 hours. Warehouse inventory: 2.1 days coverage. 8,400 pre-orders at SLA risk. Competitor stockouts confirmed."},
    {"id":3,"icon":"⚔️","tag":"COMPETITIVE","title":"Competitor Price War","description":"Primary competitor reduced prices 22% across all SKUs effective midnight. Three enterprise clients requested renegotiation calls. Customer acquisition cost up 40%. Win rate dropped 68% to 41%."},
    {"id":4,"icon":"⚙️","tag":"OPERATIONS","title":"Manufacturing Line Down","description":"Production line 3 offline due to servo motor failure. Capacity reduced 35%. Repair ETA 72 hours. Backlog at 2,000 units/day. Retail SLA breach in 96 hours."},
    {"id":5,"icon":"📉","tag":"RETENTION","title":"Customer Churn Spike","description":"Churn rate elevated 2.8x in 48 hours. NPS dropped 67 to 31. Support tickets up 180%. Billing glitch charged 1,200 accounts incorrectly. Social media sentiment negative."},
]
 
AGENT_SYSTEMS = {
    "scout":"""You are the Scout Agent in an autonomous business intelligence system.
Role: Detect and surface critical signals from business events.
Format: 3-4 bullet points covering core problem, affected stakeholders, urgency (IMMEDIATE/HIGH/MEDIUM), first-order impact. Be precise.""",
    "analyst":"""You are the Analyst Agent in an autonomous business intelligence system.
Role: Deep root-cause analysis and quantified business impact.
Format: 4-5 sentences covering root cause, financial impact in $, consequences at 24h/72h/7-day, secondary ripple effects. Be data-driven.""",
    "risk":"""You are the Risk Agent. Quantify risk precisely.
Output ONLY valid JSON, no markdown, no explanation:
{"risk_score":<0-100>,"confidence":<0-100>,"risk_level":"<CRITICAL|HIGH|MEDIUM|LOW>","primary_risk":"<max 8 words>","secondary_risk":"<max 8 words>","revenue_at_risk":"<e.g.$2.4M>","time_to_impact":"<e.g.48 hours>"}""",
    "strategy":"""You are the Strategy Agent in an autonomous business intelligence system.
Role: Formulate 3 concrete prioritized response options.
Format: Numbered 1-3. Each must have WHO (role), WHAT (action), WHEN (immediate/24h/72h), EXPECTED OUTCOME. Be decisive.""",
    "command":"""You are the Command Agent — final autonomous decision authority.
Format exactly:
[ALERT LEVEL] 🔴 CRITICAL ALERT | 🟠 HIGH ALERT | 🟡 ADVISORY | 🟢 MONITOR
 
COMMAND: <decisive action>
PRIORITY ACTION: <most important task in next 60 minutes>
ESCALATE TO: <specific role>
RATIONALE: <one sentence>
CONFIDENCE: <percentage>%""",
}
 
def call_agent(agent_id, message, api_key):
    try:
        client = Groq(api_key=api_key)
        r = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role":"system","content":AGENT_SYSTEMS[agent_id]},{"role":"user","content":message}],
            temperature=0.65, max_tokens=600,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Agent error: {e}"
 
def parse_risk(raw):
    fallback = {"risk_score":60,"confidence":65,"risk_level":"HIGH","primary_risk":"Operational disruption","secondary_risk":"Revenue impact","revenue_at_risk":"Est. $1-3M","time_to_impact":"48-72 hours"}
    try:
        return json.loads(re.sub(r"```(?:json)?|```","",raw).strip())
    except:
        m = re.search(r"\{[\s\S]+\}", raw)
        if m:
            try: return json.loads(m.group())
            except: pass
    return fallback
 
def make_gauge(score, level):
    color = {"CRITICAL":"#ff1744","HIGH":"#ffab00","MEDIUM":"#2979ff","LOW":"#00e5ff"}.get(level,"#ffab00")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font":{"color":color,"size":44,"family":"JetBrains Mono"}},
        gauge={"axis":{"range":[0,100],"tickfont":{"color":"#4a5568","size":9}},
               "bar":{"color":color,"thickness":0.22},"bgcolor":"#0c0f1a","borderwidth":0,
               "steps":[{"range":[0,25],"color":"rgba(0,229,255,0.07)"},{"range":[25,50],"color":"rgba(41,121,255,0.07)"},
                        {"range":[50,75],"color":"rgba(255,171,0,0.07)"},{"range":[75,100],"color":"rgba(255,23,68,0.07)"}],
               "threshold":{"line":{"color":color,"width":3},"thickness":0.8,"value":score}},
    ))
    fig.update_layout(height=210,margin=dict(t=30,b=10,l=20,r=20),paper_bgcolor="#0c0f1a",
        font={"family":"JetBrains Mono","color":"#94a3b8"},
        annotations=[{"text":"RISK SCORE / 100","x":0.5,"y":0.08,"showarrow":False,"font":{"size":9,"color":"#4a5568"}}])
    return fig
 
def make_history_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    colors = [{"CRITICAL":"#ff1744","HIGH":"#ffab00","MEDIUM":"#2979ff","LOW":"#00e5ff"}.get(l,"#2979ff") for l in df["level"]]
    fig = go.Figure(go.Bar(x=df["label"],y=df["score"],marker_color=colors,text=df["score"],textposition="outside"))
    fig.update_layout(height=180,margin=dict(t=10,b=10,l=10,r=10),paper_bgcolor="#0c0f1a",plot_bgcolor="#0c0f1a",
        xaxis={"showgrid":False,"tickfont":{"size":9}},
        yaxis={"gridcolor":"#1a1f2e","range":[0,115],"tickfont":{"size":9}},showlegend=False)
    return fig
 
def init():
    for k,v in [("log",[]),("outputs",{}),("risk_data",None),("history",[]),
                ("running",False),("active",None),("statuses",{a["id"]:"idle" for a in AGENTS}),("count",0)]:
        if k not in st.session_state: st.session_state[k]=v
 
def add_log(agent_id, msg, t="output"):
    a = next((x for x in AGENTS if x["id"]==agent_id),None)
    st.session_state.log.append({
        "time":datetime.now().strftime("%H:%M:%S"),
        "name":a["name"] if a else "SYS","icon":a["icon"] if a else "⬡",
        "color":a["color"] if a else "#4a5568","message":msg,"type":t})
 
def run_pipeline(title, desc, api_key, tag="CUSTOM"):
    st.session_state.running=True
    st.session_state.outputs={}
    st.session_state.log=[]
    st.session_state.risk_data=None
    st.session_state.statuses={a["id"]:"idle" for a in AGENTS}
    st.session_state.active={"title":title,"description":desc,"tag":tag}
    add_log("scout",f"⚡ Pipeline started — {title}","system")
    add_log("scout",f"📋 {desc[:120]}{'...' if len(desc)>120 else ''}","system")
    results={}
    bar=st.progress(0,text="Initializing...")
    steps=[
        ("scout","◈ Scout scanning signals...",
         lambda r,t=title,d=desc: f"Business Event: {t}\nDetails: {d}\nSurface critical signals."),
        ("analyst","◉ Analyst running deep analysis...",
         lambda r,t=title,d=desc: f"Scenario: {t}\nDetails: {d}\n\nScout:\n{r.get('scout','')}\n\nDeep analysis."),
        ("risk","◬ Risk Agent quantifying...",
         lambda r,t=title: f"Scenario: {t}\n\nAnalysis:\n{r.get('analyst','')}\n\nReturn ONLY JSON."),
        ("strategy","◆ Strategy Agent formulating...",
         lambda r,t=title: f"Scenario: {t}\nAnalysis:\n{r.get('analyst','')}\nRisk: {st.session_state.risk_data.get('risk_level','HIGH') if st.session_state.risk_data else 'HIGH'} ({st.session_state.risk_data.get('risk_score',60) if st.session_state.risk_data else 60}/100)\n\n3 strategic options."),
        ("command","★ Command issuing final decision...",
         lambda r,t=title: f"Scenario: {t}\nScout:\n{r.get('scout','')}\nAnalysis:\n{r.get('analyst','')}\nRisk: {st.session_state.risk_data.get('risk_level','HIGH') if st.session_state.risk_data else 'HIGH'} ({st.session_state.risk_data.get('risk_score',60) if st.session_state.risk_data else 60}/100)\nStrategy:\n{r.get('strategy','')}\n\nFinal command."),
    ]
    for i,(aid,thinking,build) in enumerate(steps):
        st.session_state.statuses[aid]="processing"
        add_log(aid,thinking,"thinking")
        bar.progress(i/5,text=thinking)
        output=call_agent(aid,build(results),api_key)
        results[aid]=output
        if aid=="risk":
            parsed=parse_risk(output)
            st.session_state.risk_data=parsed
            add_log(aid,f"Score:{parsed['risk_score']}/100 | Level:{parsed['risk_level']} | Revenue:{parsed.get('revenue_at_risk','N/A')} | Time:{parsed.get('time_to_impact','N/A')}")
        else:
            add_log(aid,output)
        st.session_state.outputs[aid]=output
        st.session_state.statuses[aid]="done"
        bar.progress((i+1)/5,text=f"✓ {aid.capitalize()} complete")
        time.sleep(0.1)
    rd=st.session_state.risk_data
    st.session_state.history.append({"label":" ".join(title.split()[:2]),"score":rd["risk_score"] if rd else 50,"level":rd["risk_level"] if rd else "HIGH"})
    st.session_state.count+=1
    add_log("scout","✅ Pipeline complete — decision issued","system")
    bar.progress(1.0,text="✅ Complete")
    st.session_state.running=False
 
def main():
    init()
    st.markdown("<div style='background:linear-gradient(135deg,#0d1117,#0a0e1a);border:1px solid #1e2d3d;border-radius:14px;padding:22px 32px;margin-bottom:20px;text-align:center'><h1 style='color:#00e5ff;letter-spacing:6px;font-size:28px;margin:0;text-shadow:0 0 30px rgba(0,229,255,0.5)'>🖤 DARK</h1><p style='color:#4a5568;letter-spacing:3px;font-size:10px;margin:8px 0 0'>AUTONOMOUS MULTI-AGENT DECISION INTELLIGENCE SYSTEM</p></div>",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("AGENTS ONLINE","5 / 5",delta="All Active")
    with c2: st.metric("DECISIONS MADE",st.session_state.count)
    with c3: st.metric("STATUS","🟡 PROCESSING" if st.session_state.running else "🟢 READY")
    with c4:
        rd=st.session_state.risk_data
        st.metric("LAST RISK",f"{rd['risk_score']}/100" if rd else "—",delta=rd.get("risk_level","") if rd else "")
    st.markdown("---")
    st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:3px;margin-bottom:10px'>▸ AGENT PIPELINE</p>",unsafe_allow_html=True)
    cols=st.columns(5)
    for col,agent in zip(cols,AGENTS):
        s=st.session_state.statuses.get(agent["id"],"idle")
        if s=="processing":   border,bg,gc,sl,sc=agent["color"],f"{agent['color']}12",agent["color"],"● ACTIVE","#ffab00"
        elif s=="done":       border,bg,gc,sl,sc=f"{agent['color']}55",f"{agent['color']}07",agent["color"],"✓ DONE","#00e5ff"
        else:                 border,bg,gc,sl,sc="#1a1f2e","#0c0f1a","#2d3748","○ IDLE","#1a2035"
        with col:
            st.markdown(f"<div style='background:{bg};border:1px solid {border};border-radius:10px;padding:14px 6px;text-align:center'><div style='font-size:22px;color:{gc};margin-bottom:5px'>{agent['icon']}</div><div style='font-size:10px;letter-spacing:2px;color:{gc}'>{agent['name']}</div><div style='font-size:8px;color:#2d3748'>{agent['role']}</div><div style='font-size:8px;color:{sc};margin-top:6px'>{sl}</div></div>",unsafe_allow_html=True)
    st.markdown("---")
    with st.sidebar:
        st.markdown("<h3 style='color:#00e5ff;letter-spacing:3px;font-size:14px;margin-bottom:16px'>🖤 CONTROL PANEL</h3>",unsafe_allow_html=True)
        st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px;margin-bottom:4px'>▸ GROQ API KEY (FREE)</p>",unsafe_allow_html=True)
        api_key=st.text_input("key",type="password",placeholder="gsk_xxxxxxxxxxxxxxxxxxxx",label_visibility="collapsed")
        if not api_key: st.warning("Enter Groq API key to activate agents",icon="🔑")
        else: st.success("API key loaded ✓",icon="🔐")
        st.markdown("---")
        st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px;margin-bottom:6px'>▸ QUICK PRESET SCENARIOS</p>",unsafe_allow_html=True)
        for p in PRESETS:
            if st.button(f"{p['icon']}  {p['title']}",key=f"p{p['id']}",disabled=st.session_state.running or not api_key,use_container_width=True):
                run_pipeline(p["title"],p["description"],api_key,p["tag"])
                st.rerun()
            st.markdown(f"<p style='font-size:9px;color:#2d3748;margin:-6px 0 8px 4px'>{p['tag']}</p>",unsafe_allow_html=True)
    st.markdown("<p style='color:#00e5ff;font-size:12px;letter-spacing:3px;margin-bottom:10px'>▸ YOUR CUSTOM SCENARIO</p>",unsafe_allow_html=True)
    st.markdown("<div style='background:#0c0f1a;border:1px solid rgba(0,229,255,0.15);border-radius:12px;padding:14px 18px;margin-bottom:16px'><p style='color:#4a5568;font-size:10px;margin:0 0 4px'>💡 Type ANY real business problem — 5 agents analyze it instantly</p><p style='color:#2d3748;font-size:9px;margin:0'>Works for: server outages · recalls · budget cuts · staff issues · data breaches · market changes</p></div>",unsafe_allow_html=True)
    col_a,col_b=st.columns([3,1])
    with col_a:
        st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px;margin-bottom:4px'>SCENARIO TITLE</p>",unsafe_allow_html=True)
        custom_title=st.text_input("ctitle",label_visibility="collapsed",placeholder="e.g. AWS Outage / Product Recall / Key Engineer Resigned",disabled=st.session_state.running)
    with col_b:
        st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px;margin-bottom:4px'>CATEGORY</p>",unsafe_allow_html=True)
        custom_tag=st.selectbox("ctag",label_visibility="collapsed",options=["CUSTOM","OPERATIONS","FINANCE","HR","TECHNOLOGY","MARKETING","LOGISTICS","LEGAL","SECURITY"],disabled=st.session_state.running)
    st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px;margin:12px 0 4px'>DESCRIBE THE SITUATION IN DETAIL</p>",unsafe_allow_html=True)
    custom_desc=st.text_area("cdesc",label_visibility="collapsed",height=150,
        placeholder="What happened? What is at risk? Numbers, timeline, affected teams...\n\nExample: Our payment gateway went down at 2 AM. 3,000 checkout attempts failed. We lose $8,000/hour. Black Friday is in 36 hours. Engineering has no ETA yet.",
        disabled=st.session_state.running)
    chars=len(custom_desc)
    cc="#00e5ff" if chars>=50 else "#ffab00" if chars>0 else "#2d3748"
    note="✓ Good detail" if chars>=50 else "— add more detail for better results" if chars>0 else ""
    st.markdown(f"<p style='color:{cc};font-size:9px;text-align:right;margin-top:-8px'>{chars} chars {note}</p>",unsafe_allow_html=True)
    can_run=bool(api_key and custom_title.strip() and len(custom_desc.strip())>=20 and not st.session_state.running)
    _,btn_col,_=st.columns([1,2,1])
    with btn_col:
        if st.button("🚀  ACTIVATE 5 AGENTS  →" if not st.session_state.running else "⏳  AGENTS PROCESSING...",disabled=not can_run,use_container_width=True):
            run_pipeline(custom_title.strip(),custom_desc.strip(),api_key,custom_tag)
            st.rerun()
    if not api_key: st.markdown("<p style='color:#ffab00;font-size:10px;text-align:center;margin-top:6px'>⚠️ Enter Groq API key in the sidebar first</p>",unsafe_allow_html=True)
    if st.session_state.active:
        sc=st.session_state.active
        st.markdown(f"<div style='background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.2);border-radius:10px;padding:12px 16px;margin-top:14px'><span style='font-size:9px;color:#00e5ff;background:rgba(0,229,255,0.08);border:1px solid rgba(0,229,255,0.2);padding:2px 10px;border-radius:99px'>{sc['tag']}</span>  <span style='font-size:12px;color:#e2e8f0'>{sc['title']}</span><p style='color:#4a5568;font-size:10px;line-height:1.6;margin:8px 0 0'>{sc['description'][:200]}{'...' if len(sc['description'])>200 else ''}</p></div>",unsafe_allow_html=True)
    st.markdown("---")
    left,right=st.columns([1,1],gap="large")
    with left:
        rd=st.session_state.risk_data
        if rd:
            st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px'>▸ LIVE RISK ASSESSMENT</p>",unsafe_allow_html=True)
            st.plotly_chart(make_gauge(rd["risk_score"],rd["risk_level"]),use_container_width=True)
            m1,m2,m3=st.columns(3)
            with m1: st.markdown(f"<div class='metric-box'><div style='font-size:8px;color:#4a5568'>PRIMARY RISK</div><div style='color:#ffab00;font-size:11px;margin-top:5px'>{rd.get('primary_risk','—')}</div></div>",unsafe_allow_html=True)
            with m2: st.markdown(f"<div class='metric-box'><div style='font-size:8px;color:#4a5568'>REVENUE AT RISK</div><div style='color:#ff1744;font-size:11px;margin-top:5px'>{rd.get('revenue_at_risk','—')}</div></div>",unsafe_allow_html=True)
            with m3: st.markdown(f"<div class='metric-box'><div style='font-size:8px;color:#4a5568'>TIME TO IMPACT</div><div style='color:#00e5ff;font-size:11px;margin-top:5px'>{rd.get('time_to_impact','—')}</div></div>",unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
        if st.session_state.outputs.get("command"):
            st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px'>▸ COMMAND DECISION</p>",unsafe_allow_html=True)
            st.markdown(f"<div class='command-box'>{st.session_state.outputs['command']}</div>",unsafe_allow_html=True)
            st.markdown("<br>",unsafe_allow_html=True)
        if st.session_state.history:
            st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px'>▸ DECISION HISTORY</p>",unsafe_allow_html=True)
            fig=make_history_chart(st.session_state.history)
            if fig: st.plotly_chart(fig,use_container_width=True)
        if st.session_state.outputs:
            st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px'>▸ AGENT OUTPUTS</p>",unsafe_allow_html=True)
            for agent in AGENTS:
                if agent["id"] in st.session_state.outputs and agent["id"] not in ("command","risk"):
                    with st.expander(f"{agent['icon']}  {agent['name']} — {agent['role']}"):
                        st.markdown(f"<div style='font-size:12px;color:#94a3b8;line-height:1.75;font-family:monospace;white-space:pre-wrap'>{st.session_state.outputs[agent['id']]}</div>",unsafe_allow_html=True)
    with right:
        st.markdown("<p style='color:#4a5568;font-size:10px;letter-spacing:2px'>▸ AGENT COMMUNICATION LOG</p>",unsafe_allow_html=True)
        if not st.session_state.log:
            st.markdown("<div style='text-align:center;color:#2d3748;padding:60px 20px'><div style='font-size:40px'>🖤</div><div style='font-size:11px;letter-spacing:2px;margin-top:12px'>TYPE YOUR SCENARIO ABOVE</div><div style='font-size:9px;margin-top:6px;color:#1a2035'>OR PICK A PRESET FROM THE SIDEBAR</div></div>",unsafe_allow_html=True)
        for entry in st.session_state.log:
            bg="#001512" if entry["type"]=="system" else ("#0c0f1a" if entry["type"]=="thinking" else "#0f1320")
            tc="#94a3b8" if entry["type"]!="thinking" else "#4a5568"
            fs="italic" if entry["type"]=="thinking" else "normal"
            st.markdown(f"<div style='margin-bottom:10px'><div style='display:flex;justify-content:space-between;margin-bottom:3px'><span style='font-size:10px;color:{entry['color']};letter-spacing:1px'>{entry['icon']} {entry['name']}</span><span style='font-size:9px;color:#2d3748'>{entry['time']}</span></div><div style='font-size:11px;line-height:1.65;padding:8px 12px;border-radius:6px;background:{bg};border:1px solid {entry['color']}30;color:{tc};font-style:{fs};white-space:pre-wrap;font-family:monospace'>{entry['message']}</div></div>",unsafe_allow_html=True)
        if st.session_state.log:
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🗑  Clear Log",use_container_width=True):
                st.session_state.log=[]
                st.rerun()
 
if __name__=="__main__":
    main()
