from __future__ import annotations

import os
import sqlite3
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    from supabase import create_client
except Exception:
    create_client = None

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SQLITE_PATH = DATA_DIR / "human_rhythms.sqlite3"

st.set_page_config(
    page_title="HUMAN RHYTHMS",
    page_icon="◌",
    layout="wide",
    initial_sidebar_state="expanded",
)

DOMAINS = {
    "Biological & circadian": ["sleep_duration", "sleep_quality", "sleep_timing", "daytime_alertness", "light_exposure"],
    "Physical": ["physical_energy", "movement", "physical_recovery", "physical_function"],
    "Emotional": ["mood", "stress", "emotional_regulation", "positive_affect"],
    "Cognitive": ["focus", "mental_energy", "memory", "learning"],
    "Behavioral": ["routine_consistency", "task_initiation", "self_regulation"],
    "Social": ["social_connection", "social_support", "social_demand"],
    "Environmental": ["daylight_access", "noise", "thermal_comfort", "workspace_quality"],
    "Occupational & time use": ["workload", "schedule_control", "time_alignment", "perceived_productivity"],
    "Meaning & recovery": ["purpose", "leisure", "restoration", "reflection"],
}
DOMAIN_COLORS = {
    "Biological & circadian": "#D8C49A",
    "Physical": "#8CB7A5",
    "Emotional": "#C98F9B",
    "Cognitive": "#8EA9D1",
    "Behavioral": "#B7A1D2",
    "Social": "#D6A879",
    "Environmental": "#83B8BD",
    "Occupational & time use": "#A7AEB8",
    "Meaning & recovery": "#C2B58A",
}
DOMAIN_DESCRIPTIONS = {
    "Biological & circadian": "Sleep-wake timing, sleep experience, alertness and light exposure.",
    "Physical": "Perceived energy, movement, recovery and physical functioning.",
    "Emotional": "Mood, stress and perceived emotional regulation.",
    "Cognitive": "Attention, mental energy, memory and learning.",
    "Behavioral": "Routines, task initiation and self-regulation.",
    "Social": "Connection, support and social demands.",
    "Environmental": "Daylight, noise, thermal comfort and workspace conditions.",
    "Occupational & time use": "Workload, schedule control, time alignment and perceived productivity.",
    "Meaning & recovery": "Purpose, leisure, restoration and reflection.",
}
PERIODS = ["Today", "9 days", "1 week", "1 month", "3 months", "6 months", "1 year", "2 years", "Lifetime", "Custom"]
RATING_FIELDS = {
    "physical_energy": "Physical energy",
    "physical_recovery": "Physical recovery",
    "physical_function": "Physical functioning",
    "mood": "Mood",
    "stress": "Stress",
    "emotional_regulation": "Emotional regulation",
    "positive_affect": "Positive affect",
    "focus": "Focus / attention",
    "mental_energy": "Mental energy",
    "memory": "Memory",
    "learning": "Learning",
    "routine_consistency": "Routine consistency",
    "task_initiation": "Task initiation",
    "self_regulation": "Self-regulation",
    "social_connection": "Social connection",
    "social_support": "Social support",
    "social_demand": "Social demand",
    "daylight_access": "Daylight access",
    "noise": "Noise burden",
    "thermal_comfort": "Thermal comfort",
    "workspace_quality": "Workspace quality",
    "workload": "Workload",
    "schedule_control": "Schedule control",
    "time_alignment": "Time-use alignment",
    "perceived_productivity": "Perceived productivity",
    "purpose": "Sense of purpose",
    "leisure": "Leisure",
    "restoration": "Restoration",
    "reflection": "Reflection",
}
INVERTED = {"stress", "social_demand", "noise", "workload"}
NUMERIC_FIELDS = {
    "sleep_duration": "Sleep duration (hours)",
    "sleep_quality": "Sleep quality (1–5)",
    "sleep_timing": "Sleep timing alignment (1–5)",
    "daytime_alertness": "Daytime alertness (1–5)",
    "light_exposure": "Outdoor/daylight exposure (minutes)",
    "movement": "Movement / exercise (minutes)",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp { background: #0b0e12; color: #e8e9eb; }
[data-testid="stSidebar"] { background: #0e1218; border-right: 1px solid #222a33; }
h1,h2,h3 { letter-spacing: -0.035em; }
h1 { font-weight: 600; }
.small-mono, .metric-label { font-family: 'DM Mono', monospace; letter-spacing: .04em; text-transform: uppercase; color: #9099a5; font-size: .68rem; }
.metric-value { font-family: 'DM Mono', monospace; font-size: 1.7rem; color: #e9e4d9; }
.panel { background: #11161d; border: 1px solid #242d38; border-radius: 9px; padding: 15px 17px; }
.muted { color: #929ba7; }
.gold { color: #b6a27a; }
div[data-testid="stMetric"] { background: #11161d; border: 1px solid #242d38; padding: 12px 14px; border-radius: 8px; }
div[data-testid="stMetricLabel"] p { color: #929ba7; font-family: 'DM Mono', monospace; font-size: .68rem; text-transform: uppercase; }
div[data-testid="stMetricValue"] { font-family: 'DM Mono', monospace; }
hr { border-color: #242d38; }
.stButton button, .stDownloadButton button { border-radius: 6px; }
footer { visibility: hidden; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# -------------------------- persistence --------------------------

def sqlite_conn():
    conn = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_sqlite():
    with sqlite_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY, display_name TEXT, birth_date TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, observed_at TEXT NOT NULL,
            domain TEXT NOT NULL, indicator TEXT NOT NULL, value REAL NOT NULL, unit TEXT,
            scale_min REAL, scale_max REAL, source TEXT NOT NULL DEFAULT 'self_report',
            confidence INTEGER, notes TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_observations_profile_time ON observations(profile_id, observed_at);
        CREATE INDEX IF NOT EXISTS idx_observations_indicator ON observations(profile_id, indicator);
        CREATE TABLE IF NOT EXISTS life_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, label TEXT NOT NULL,
            start_date TEXT NOT NULL, end_date TEXT, description TEXT, recall_confidence INTEGER,
            source TEXT NOT NULL DEFAULT 'retrospective_self_report', created_at TEXT NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS life_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, event_date TEXT NOT NULL,
            title TEXT NOT NULL, category TEXT, description TEXT, impact_domains TEXT,
            recall_confidence INTEGER, source TEXT NOT NULL DEFAULT 'retrospective_self_report',
            created_at TEXT NOT NULL, FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, activity_date TEXT NOT NULL,
            activity TEXT NOT NULL, category TEXT, duration_minutes INTEGER, notes TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS daily_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL, checkin_date TEXT NOT NULL,
            bedtime TEXT, wake_time TEXT, sleep_duration REAL, daylight_minutes INTEGER,
            movement_minutes INTEGER, work_study_minutes INTEGER, reflection TEXT, created_at TEXT NOT NULL,
            UNIQUE(profile_id, checkin_date), FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );
        """)


def supabase_client():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
    if url and key and create_client:
        try:
            return create_client(url, key)
        except Exception as e:
            st.warning(f"Supabase connection could not be initialized: {e}")
    return None


def backend():
    sb = supabase_client()
    return ("supabase", sb) if sb else ("sqlite", None)


def current_profile_id():
    return st.session_state.get("profile_id", "local-user")


def ensure_profile():
    pid = current_profile_id()
    name = st.session_state.get("display_name", "My profile")
    dob = st.session_state.get("birth_date")
    now = datetime.utcnow().isoformat(timespec="seconds")
    mode, sb = backend()
    if mode == "supabase":
        try:
            sb.table("profiles").upsert({"id": pid, "display_name": name, "birth_date": dob.isoformat() if dob else None}).execute()
            return
        except Exception as e:
            st.error(f"Supabase write failed. Check SQL setup and authentication: {e}")
            st.stop()
    with sqlite_conn() as c:
        c.execute("""INSERT INTO profiles(id,display_name,birth_date,created_at,updated_at)
        VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name,
        birth_date=excluded.birth_date,updated_at=excluded.updated_at""",
        (pid, name, dob.isoformat() if dob else None, now, now))


def insert_rows(table, rows):
    if not rows:
        return
    mode, sb = backend()
    if mode == "supabase":
        sb.table(table).insert(rows).execute()
        return
    allowed = {
        "observations": ["profile_id","observed_at","domain","indicator","value","unit","scale_min","scale_max","source","confidence","notes","created_at"],
        "life_periods": ["profile_id","label","start_date","end_date","description","recall_confidence","source","created_at"],
        "life_events": ["profile_id","event_date","title","category","description","impact_domains","recall_confidence","source","created_at"],
        "activities": ["profile_id","activity_date","activity","category","duration_minutes","notes","created_at"],
    }
    cols = allowed[table]
    with sqlite_conn() as c:
        c.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})",
                      [[r.get(k) for k in cols] for r in rows])


def read_table(table, filters=None):
    mode, sb = backend()
    pid = current_profile_id()
    if mode == "supabase":
        q = sb.table(table).select("*").eq("profile_id", pid)
        if table in ("observations", "daily_checkins"):
            q = q.order("observed_at" if table == "observations" else "checkin_date")
        elif table == "life_events":
            q = q.order("event_date")
        elif table == "life_periods":
            q = q.order("start_date")
        elif table == "activities":
            q = q.order("activity_date")
        data = q.execute().data or []
        return pd.DataFrame(data)
    with sqlite_conn() as c:
        df = pd.read_sql_query(f"SELECT * FROM {table} WHERE profile_id = ?", c, params=(pid,))
    return df


def delete_record(table, record_id):
    mode, sb = backend()
    if mode == "supabase":
        sb.table(table).delete().eq("id", record_id).eq("profile_id", current_profile_id()).execute()
    else:
        with sqlite_conn() as c:
            c.execute(f"DELETE FROM {table} WHERE id=? AND profile_id=?", (record_id, current_profile_id()))


init_sqlite()
mode, sb = backend()
if "profile_id" not in st.session_state:
    st.session_state.profile_id = "local-user"
if "display_name" not in st.session_state:
    st.session_state.display_name = "My profile"
if "birth_date" not in st.session_state:
    st.session_state.birth_date = None


# -------------------------- data helpers --------------------------

def frame(table):
    try:
        return read_table(table)
    except Exception as e:
        st.error(f"Could not read {table}: {e}")
        return pd.DataFrame()


def add_observation(observed_at, domain, indicator, value, unit=None, scale_min=None, scale_max=None,
                    source="self_report", confidence=None, notes=None):
    row = {
        "profile_id": current_profile_id(), "observed_at": observed_at.isoformat(),
        "domain": domain, "indicator": indicator, "value": float(value), "unit": unit,
        "scale_min": scale_min, "scale_max": scale_max, "source": source,
        "confidence": confidence, "notes": notes, "created_at": datetime.utcnow().isoformat(timespec="seconds")
    }
    insert_rows("observations", [row])


def add_rating_observation(observed_at, domain, indicator, value, notes=""):
    # Ratings are stored as 1–5 raw self-reports. Normalized chart values are a display transform only.
    add_observation(observed_at, domain, indicator, value, "rating_1_5", 1, 5, "self_report", 3, notes)


def normalize_for_chart(df):
    if df.empty:
        return df
    out = df.copy()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out["observed_at"] = pd.to_datetime(out["observed_at"], errors="coerce")
    def transform(r):
        v = r["value"]
        ind = r["indicator"]
        if pd.isna(v):
            return None
        if ind in INVERTED and r.get("scale_min") is not None and r.get("scale_max") is not None:
            return (float(r["scale_max"]) - v) / (float(r["scale_max"]) - float(r["scale_min"])) * 100
        if r.get("scale_min") is not None and r.get("scale_max") is not None and float(r["scale_max"]) != float(r["scale_min"]):
            return (v - float(r["scale_min"])) / (float(r["scale_max"]) - float(r["scale_min"])) * 100
        if ind in ("sleep_duration", "light_exposure", "movement"):
            return None
        return None
    out["chart_value"] = out.apply(transform, axis=1)
    out.loc[out["chart_value"].notna(), "chart_value"] = out.loc[out["chart_value"].notna(), "chart_value"].clip(0, 100)
    return out


def period_start(period, ref_date, dob):
    if period == "Today": return ref_date
    if period == "9 days": return ref_date - timedelta(days=8)
    if period == "1 week": return ref_date - timedelta(days=6)
    if period == "1 month": return ref_date - pd.DateOffset(months=1).to_pytimedelta()
    if period == "3 months": return ref_date - pd.DateOffset(months=3).to_pytimedelta()
    if period == "6 months": return ref_date - pd.DateOffset(months=6).to_pytimedelta()
    if period == "1 year": return ref_date - pd.DateOffset(years=1).to_pytimedelta()
    if period == "2 years": return ref_date - pd.DateOffset(years=2).to_pytimedelta()
    if period == "Lifetime": return dob or date(1900,1,1)
    return ref_date - timedelta(days=30)


def domain_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["domain","chart_value"])
    normalized = normalize_for_chart(df)
    return normalized.dropna(subset=["chart_value"]).groupby("domain", as_index=False)["chart_value"].mean()


def latest_state(df):
    if df.empty:
        return pd.DataFrame()
    d = normalize_for_chart(df).dropna(subset=["chart_value"]).sort_values("observed_at")
    if d.empty: return pd.DataFrame()
    return d.groupby("domain", as_index=False).tail(1).sort_values("domain")


def chart_theme(fig, height=520):
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0b0e12", plot_bgcolor="#0b0e12",
        font=dict(family="Inter", color="#cbd0d6", size=11),
        height=height, margin=dict(l=20,r=20,t=40,b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor="#343d48", zeroline=False)
    fig.update_yaxes(gridcolor="#222a33", zeroline=False, range=[0,100], title="Display scale (0–100)")
    return fig


def export_workbook():
    tables = {t: frame(t) for t in ["observations","life_periods","life_events","activities"]}
    profile = pd.DataFrame([{"profile_id":current_profile_id(),"display_name":st.session_state.display_name,
                              "birth_date":str(st.session_state.birth_date or "")}])
    path = DATA_DIR / "human_rhythms_export.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        profile.to_excel(writer, sheet_name="Profile", index=False)
        for name, df in tables.items():
            df.to_excel(writer, sheet_name=name[:31].title(), index=False)
    return path


# -------------------------- navigation --------------------------

with st.sidebar:
    st.markdown("## HUMAN RHYTHMS")
    st.markdown("<div class='small-mono'>PERSONAL RHYTHM OBSERVATORY · 0.2</div>", unsafe_allow_html=True)
    st.divider()
    page = st.radio("Workspace", ["Rhythm Map", "Record observations", "Life history", "Analytics", "Data & settings", "Method"], label_visibility="collapsed")
    st.divider()
    st.markdown("<div class='small-mono'>DATA BACKEND</div>", unsafe_allow_html=True)
    st.markdown(f"**{'SUPABASE / POSTGRESQL' if mode == 'supabase' else 'LOCAL SQLITE'}**")
    st.caption("Hosted database" if mode == "supabase" else "Local database · data stays on this machine")
    if st.button("Refresh data", use_container_width=True):
        st.rerun()
    st.divider()
    st.caption("Observational system · not a diagnostic instrument")

obs = frame("observations")
periods = frame("life_periods")
events = frame("life_events")
activities = frame("activities")

# -------------------------- rhythm map --------------------------

if page == "Rhythm Map":
    st.markdown("# Human state")
    st.markdown("One synchronized view of nine domains across time.")
    p1, p2, p3 = st.columns([1.2,1,1])
    with p1:
        period = st.selectbox("Temporal window", PERIODS, index=1)
    with p2:
        ref_date = st.date_input("Reference date", value=date.today())
    with p3:
        compare = st.toggle("Show domain averages", value=False)
    custom_from, custom_to = None, None
    if period == "Custom":
        c1,c2 = st.columns(2)
        custom_from = c1.date_input("From", value=date.today()-timedelta(days=30))
        custom_to = c2.date_input("To", value=date.today())
    dob = st.session_state.birth_date
    start = custom_from if period == "Custom" else period_start(period, ref_date, dob)
    end = custom_to if period == "Custom" else ref_date
    if not obs.empty:
        data = normalize_for_chart(obs)
        data = data[(data["observed_at"].dt.date >= start) & (data["observed_at"].dt.date <= end)]
        chart_data = data.dropna(subset=["chart_value"]).copy()
    else:
        chart_data = pd.DataFrame()
    if chart_data.empty:
        st.info("No chartable observations in this time window yet. Record a check-in to start building your rhythm map.")
        st.markdown("### What becomes visible")
        st.markdown("Each domain develops its own time series as you collect observations. The chart does not fabricate missing history.")
    else:
        latest = latest_state(chart_data)
        metric_cols = st.columns(3)
        metric_cols[0].metric("Domains with observations", f"{latest['domain'].nunique()} / 9")
        metric_cols[1].metric("Recorded observations", f"{len(chart_data):,}")
        metric_cols[2].metric("Latest observation", chart_data["observed_at"].max().strftime("%d %b %Y"))
        fig = go.Figure()
        for domain in DOMAINS:
            d = chart_data[chart_data["domain"] == domain].sort_values("observed_at")
            if d.empty: continue
            fig.add_trace(go.Scatter(
                x=d["observed_at"], y=d["chart_value"], mode="lines+markers",
                name=domain, line=dict(width=2, color=DOMAIN_COLORS[domain]),
                marker=dict(size=5), customdata=d[["indicator","value","unit","source"]].astype(str).values,
                hovertemplate="<b>%{fullData.name}</b><br>%{x|%d %b %Y %H:%M}<br>Display: %{y:.0f}/100<br>%{customdata[0]}: %{customdata[1]} %{customdata[2]}<br>Source: %{customdata[3]}<extra></extra>"
            ))
        if compare:
            summary = chart_data.groupby("domain",as_index=False)["chart_value"].mean()
            for _, r in summary.iterrows():
                fig.add_hline(y=r["chart_value"], line_dash="dot", opacity=.18, line_color=DOMAIN_COLORS.get(r["domain"],"#aaa"))
        chart_theme(fig, 580)
        fig.update_layout(title="SYNCHRONIZED DOMAIN SERIES", yaxis_title="Normalized display value (0–100)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("The 0–100 axis is a display transformation of selected 1–5 self-ratings. It is not a validated health score or a common physical unit. Raw observations remain available below.")
        with st.expander("Latest recorded state by domain", expanded=True):
            latest = latest_state(chart_data)
            if latest.empty:
                st.write("No normalized ratings in this window.")
            else:
                for _, r in latest.iterrows():
                    st.markdown(f"**{r['domain']}** · {r['indicator'].replace('_',' ')} · {r['value']:g}/5 · {r['observed_at'].strftime('%d %b %Y %H:%M')}")
        with st.expander("Inspect raw observations"):
            st.dataframe(chart_data[["observed_at","domain","indicator","value","unit","source","confidence","notes"]], use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("### Current state is based on your latest records")
    st.caption("This is not a live sensor feed. The dashboard updates when you enter or import new observations. A domain without recent data is unknown, not zero.")

# -------------------------- observation entry --------------------------

elif page == "Record observations":
    st.markdown("# Record observations")
    st.markdown("Capture what you observe now. A timestamped record becomes a point in the synchronized map.")
    with st.form("observation_form"):
        c1,c2 = st.columns(2)
        observed_date = c1.date_input("Observation date", value=date.today())
        observed_time = c2.time_input("Observation time", value=datetime.now().time().replace(second=0,microsecond=0))
        st.markdown("#### Biological & circadian")
        a,b,c = st.columns(3)
        sleep_hours = a.number_input("Sleep duration (hours)", 0.0, 24.0, 7.0, .25)
        sleep_quality = b.slider("Sleep quality",1,5,3)
        alertness = c.slider("Daytime alertness",1,5,3)
        d,e,f = st.columns(3)
        sleep_timing = d.slider("Sleep timing alignment",1,5,3)
        daylight = e.number_input("Daylight / outdoor exposure (min)",0,1440,30,5)
        movement = f.number_input("Movement / exercise (min)",0,1440,30,5)
        st.markdown("#### Physical")
        p1,p2,p3 = st.columns(3)
        physical_energy = p1.slider("Physical energy",1,5,3)
        physical_recovery = p2.slider("Physical recovery",1,5,3)
        physical_function = p3.slider("Physical functioning",1,5,3)
        st.markdown("#### Emotional")
        e1,e2,e3,e4 = st.columns(4)
        mood = e1.slider("Mood",1,5,3)
        stress = e2.slider("Stress",1,5,3)
        emotional_regulation = e3.slider("Emotional regulation",1,5,3)
        positive_affect = e4.slider("Positive affect",1,5,3)
        st.markdown("#### Cognitive")
        c1,c2,c3,c4 = st.columns(4)
        focus = c1.slider("Focus",1,5,3)
        mental_energy = c2.slider("Mental energy",1,5,3)
        memory = c3.slider("Memory",1,5,3)
        learning = c4.slider("Learning",1,5,3)
        st.markdown("#### Behavioral")
        b1,b2,b3 = st.columns(3)
        routine_consistency = b1.slider("Routine consistency",1,5,3)
        task_initiation = b2.slider("Task initiation",1,5,3)
        self_regulation = b3.slider("Self-regulation",1,5,3)
        st.markdown("#### Social")
        s1,s2,s3 = st.columns(3)
        social_connection = s1.slider("Social connection",1,5,3)
        social_support = s2.slider("Social support",1,5,3)
        social_demand = s3.slider("Social demands",1,5,3)
        st.markdown("#### Environmental")
        n1,n2,n3,n4 = st.columns(4)
        daylight_access = n1.slider("Daylight access",1,5,3)
        noise = n2.slider("Noise burden",1,5,3)
        thermal_comfort = n3.slider("Thermal comfort",1,5,3)
        workspace_quality = n4.slider("Workspace quality",1,5,3)
        st.markdown("#### Occupational & time use")
        o1,o2,o3,o4 = st.columns(4)
        workload = o1.slider("Workload",1,5,3)
        schedule_control = o2.slider("Schedule control",1,5,3)
        time_alignment = o3.slider("Time-use alignment",1,5,3)
        perceived_productivity = o4.slider("Perceived productivity",1,5,3)
        st.markdown("#### Meaning & recovery")
        m1,m2,m3,m4 = st.columns(4)
        purpose = m1.slider("Purpose",1,5,3)
        leisure = m2.slider("Leisure",1,5,3)
        restoration = m3.slider("Restoration",1,5,3)
        reflection = m4.slider("Reflection",1,5,3)
        notes = st.text_area("Context / notes", placeholder="What might help interpret today's observations?")
        confidence = st.select_slider("How confident are you in these ratings?", options=[1,2,3,4,5], value=3)
        submitted = st.form_submit_button("Save observation set", type="primary", use_container_width=True)
    if submitted:
        dt = datetime.combine(observed_date, observed_time)
        values = {
            "sleep_duration":(sleep_hours,"hours"), "sleep_quality":(sleep_quality,"rating_1_5"),
            "sleep_timing":(sleep_timing,"rating_1_5"), "daytime_alertness":(alertness,"rating_1_5"),
            "light_exposure":(daylight,"minutes"), "movement":(movement,"minutes"),
        }
        for k,v in {
            "physical_energy":physical_energy,"physical_recovery":physical_recovery,"physical_function":physical_function,
            "mood":mood,"stress":stress,"emotional_regulation":emotional_regulation,"positive_affect":positive_affect,
            "focus":focus,"mental_energy":mental_energy,"memory":memory,"learning":learning,
            "routine_consistency":routine_consistency,"task_initiation":task_initiation,"self_regulation":self_regulation,
            "social_connection":social_connection,"social_support":social_support,"social_demand":social_demand,
            "daylight_access":daylight_access,"noise":noise,"thermal_comfort":thermal_comfort,"workspace_quality":workspace_quality,
            "workload":workload,"schedule_control":schedule_control,"time_alignment":time_alignment,
            "perceived_productivity":perceived_productivity,"purpose":purpose,"leisure":leisure,
            "restoration":restoration,"reflection":reflection
        }.items():
            values[k]=(v,"rating_1_5")
        rows=[]
        for indicator,(value,unit) in values.items():
            domain=next((d for d, inds in DOMAINS.items() if indicator in inds), "Other")
            rows.append({"profile_id":current_profile_id(),"observed_at":dt.isoformat(),"domain":domain,"indicator":indicator,
                         "value":float(value),"unit":unit,"scale_min":1 if unit=="rating_1_5" else None,
                         "scale_max":5 if unit=="rating_1_5" else None,"source":"self_report","confidence":confidence,
                         "notes":notes,"created_at":datetime.utcnow().isoformat(timespec="seconds")})
        insert_rows("observations",rows)
        st.success(f"Saved {len(rows)} observations at {dt:%d %b %Y, %H:%M}.")
        st.rerun()
    st.caption("All sliders are subjective self-reports, not clinical scales. Higher stress, noise burden, social demand and workload are reverse-transformed for display only.")

# -------------------------- life history --------------------------

elif page == "Life history":
    st.markdown("# Life history")
    st.markdown("Build a retrospective map of life phases and major transitions. Historical records are not equivalent to daily measurements.")
    st.markdown("### Add a life period")
    with st.form("life_period_form"):
        a,b = st.columns(2)
        label = a.text_input("Period label", placeholder="e.g. Adolescence, university years")
        start_date = b.date_input("Start date", value=date(2000,1,1), key="life_start")
        c,d = st.columns(2)
        end_date = c.date_input("End date (if completed)", value=None, key="life_end")
        recall = d.slider("Recall confidence",1,5,3)
        description = st.text_area("What characterized this period?", placeholder="Sleep-wake pattern, physical state, mood, cognitive functioning, social context, schedule...")
        if st.form_submit_button("Save life period"):
            insert_rows("life_periods",[{"profile_id":current_profile_id(),"label":label or "Unnamed period",
                "start_date":start_date.isoformat(),"end_date":end_date.isoformat() if end_date else None,
                "description":description,"recall_confidence":recall,"source":"retrospective_self_report",
                "created_at":datetime.utcnow().isoformat(timespec="seconds")}])
            st.success("Life period saved.")
            st.rerun()
    st.divider()
    st.markdown("### Add a major event or transition")
    with st.form("life_event_form"):
        a,b = st.columns(2)
        event_date = a.date_input("Approximate event date", value=date.today(), key="event_date")
        title = b.text_input("Event", placeholder="e.g. Started university, moved city, changed work schedule")
        category = st.selectbox("Category",["Education","Work","Health / physical","Relationships / social","Environment","Sleep / routine","Other"])
        description = st.text_area("Description and possible relevance")
        impacted = st.multiselect("Domains potentially affected", list(DOMAINS.keys()))
        event_recall = st.slider("Recall confidence",1,5,3,key="event_recall")
        if st.form_submit_button("Save event"):
            insert_rows("life_events",[{"profile_id":current_profile_id(),"event_date":event_date.isoformat(),
                "title":title or "Untitled event","category":category,"description":description,
                "impact_domains":json.dumps(impacted),"recall_confidence":event_recall,
                "source":"retrospective_self_report","created_at":datetime.utcnow().isoformat(timespec="seconds")}])
            st.success("Event saved.")
            st.rerun()
    st.divider()
    if not periods.empty:
        st.markdown("### Recorded life periods")
        for _,r in periods.sort_values("start_date").iterrows():
            end = r.get("end_date")
            st.markdown(f"**{r['label']}** · {r['start_date']} → {end if pd.notna(end) and end else 'present / ongoing'} · recall {r.get('recall_confidence','—')}/5")
            if pd.notna(r.get("description")) and r.get("description"):
                st.caption(r["description"])
    if not events.empty:
        st.markdown("### Life events")
        ev=events.copy()
        ev["event_date"]=pd.to_datetime(ev["event_date"])
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=ev["event_date"],y=[1]*len(ev),mode="markers+text",
                                 text=ev["title"],textposition="top center",marker=dict(size=10,color="#B6A27A"),
                                 hovertemplate="%{x|%d %b %Y}<br>%{text}<extra></extra>"))
        fig.update_layout(template="plotly_dark",paper_bgcolor="#0b0e12",plot_bgcolor="#0b0e12",height=220,
                          margin=dict(l=10,r=10,t=35,b=10),showlegend=False,yaxis=dict(visible=False),xaxis=dict(showgrid=False))
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(events[["event_date","title","category","description","recall_confidence"]],use_container_width=True,hide_index=True)
    if periods.empty and events.empty:
        st.info("No retrospective life history has been entered yet.")

# -------------------------- analytics --------------------------

elif page == "Analytics":
    st.markdown("# Research & analytics")
    st.markdown("Descriptive patterns from recorded observations. Associations are exploratory and do not establish causation.")
    if obs.empty:
        st.info("Record observations before analytics become available.")
    else:
        d=normalize_for_chart(obs)
        d["observed_at"]=pd.to_datetime(d["observed_at"])
        d["date"]=d["observed_at"].dt.date
        chart=d.dropna(subset=["chart_value"])
        if not chart.empty:
            summary=chart.groupby(["domain","indicator"],as_index=False).agg(
                observations=("value","count"),mean_raw=("value","mean"),mean_display=("chart_value","mean"),
                first_seen=("observed_at","min"),last_seen=("observed_at","max"))
            st.markdown("### Indicator summary")
            st.dataframe(summary,use_container_width=True,hide_index=True)
            st.markdown("### Domain coverage")
            coverage=chart.groupby("domain").size().reindex(DOMAINS.keys(),fill_value=0).reset_index(name="records")
            fig=px.bar(coverage,x="domain",y="records",color="domain",color_discrete_map=DOMAIN_COLORS)
            fig.update_layout(template="plotly_dark",paper_bgcolor="#0b0e12",plot_bgcolor="#0b0e12",showlegend=False,
                              xaxis_title="",yaxis_title="Records",height=330,margin=dict(l=10,r=10,t=20,b=80))
            st.plotly_chart(fig,use_container_width=True)
            st.markdown("### Indicator trends")
            indicator=st.selectbox("Select indicator",sorted(chart["indicator"].unique()))
            x=chart[chart["indicator"]==indicator].sort_values("observed_at")
            fig=px.line(x,x="observed_at",y="value",markers=True,hover_data=["domain","unit","source"])
            fig.update_layout(template="plotly_dark",paper_bgcolor="#0b0e12",plot_bgcolor="#0b0e12",
                              xaxis_title="",yaxis_title="Raw recorded value",height=370)
            st.plotly_chart(fig,use_container_width=True)
            st.caption("Trend charts use raw values and their original units. Do not compare different indicators as though they shared a measurement scale.")
        else:
            st.info("The current records do not contain normalized rating indicators.")

# -------------------------- data and settings --------------------------

elif page == "Data & settings":
    st.markdown("# Data & settings")
    st.markdown("Configure your profile, inspect records, and export a portable workbook.")
    with st.form("profile_form"):
        name=st.text_input("Display name",value=st.session_state.display_name)
        birth=st.date_input("Date of birth",value=st.session_state.birth_date or date(1990,1,1),min_value=date(1900,1,1),max_value=date.today())
        if st.form_submit_button("Save profile"):
            st.session_state.display_name=name
            st.session_state.birth_date=birth
            ensure_profile()
            st.success("Profile saved.")
    st.divider()
    st.markdown("### Database connection")
    if mode=="supabase":
        st.success("Supabase credentials detected. The app is configured to use Supabase.")
        st.caption("The database schema and Row Level Security policies must be applied from supabase/migrations/001_initial_schema.sql.")
    else:
        st.info("Using local SQLite. To connect Supabase, add SUPABASE_URL and SUPABASE_ANON_KEY to .streamlit/secrets.toml or environment variables.")
    st.code('SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"\nSUPABASE_ANON_KEY = "YOUR_SUPABASE_PUBLISHABLE_OR_ANON_KEY"',language="toml")
    st.caption("Never commit secrets.toml or service-role keys. For a multi-user deployment, implement Supabase Auth and derive the profile ID from the authenticated user; this prototype's local-user identity is for a single-user local workflow.")
    st.divider()
    c1,c2=st.columns(2)
    with c1:
        if st.button("Prepare Excel export",type="primary",use_container_width=True):
            path=export_workbook()
            st.session_state.export_ready=True
        if st.session_state.get("export_ready") and (DATA_DIR/"human_rhythms_export.xlsx").exists():
            st.download_button("Download workbook",data=(DATA_DIR/"human_rhythms_export.xlsx").read_bytes(),
                               file_name="human_rhythms_export.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
    with c2:
        st.metric("Observation records",len(obs))
        st.metric("Life periods / events",f"{len(periods)} / {len(events)}")
    with st.expander("Raw observations"):
        st.dataframe(obs,use_container_width=True,hide_index=True)
    with st.expander("Activities"):
        st.dataframe(activities,use_container_width=True,hide_index=True)
    st.warning("Privacy: do not deploy a public instance for private data until authentication, per-user authorization, and database policies have been tested.")

# -------------------------- method --------------------------

elif page == "Method":
    st.markdown("# Method & interpretation")
    st.markdown("### What this system is")
    st.write("A longitudinal personal observation system for biological timing, human functioning, time use and performance. It combines repeated prospective observations with explicitly labeled retrospective life-history records.")
    st.markdown("### What the 0–100 chart means")
    st.write("Only selected 1–5 self-rating indicators are transformed linearly to a 0–100 display scale. Reverse-coded items (stress, noise burden, social demand and workload) are inverted for visual orientation. This transformation is a display convenience, not a validated score, norm, diagnosis, or common physical unit.")
    st.markdown("### What the chart does not mean")
    st.write("- It does not measure endogenous circadian phase or biological clock timing.")
    st.write("- It does not infer chronotype.")
    st.write("- It does not diagnose health or mental-health conditions.")
    st.write("- It does not infer a true real-time physiological state or connect to wearable sensors.")
    st.write("- It does not reconstruct daily values before observations began.")
    st.write("- It does not treat missing data as zero.")
    st.markdown("### Temporal interpretation")
    st.write("The chart supports day-to-lifetime windows, but data density depends on the observations available. A smooth-looking line is not evidence of a biological oscillation. Circadian claims require appropriate repeated timing measurements and methods.")
    st.markdown("### Research alignment")
    st.write("The research protocol's six conceptual domains remain the scientific framing. The app's nine domains are an operational interface taxonomy, not nine validated constructs.")
    st.markdown("### Sources and provenance")
    st.write("Every observation should retain timestamp, indicator, unit, source, confidence and notes. Retrospective records carry recall confidence and are displayed as historical context rather than equivalent daily measurements.")
    st.markdown("### Recommended next research layer")
    st.write("Introduce validated instruments selectively (for example, a validated chronotype questionnaire) only after reviewing licensing, language validation, scoring rules and intended use. Do not create an ad hoc chronotype score.")

# first-run profile persistence
if st.session_state.birth_date:
    ensure_profile()
