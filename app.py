"""app.py - Khwezi Mining Health, Safety and Equipment Monitoring Application (Streamlit).
Run with:  streamlit run app.py"""
import pandas as pd
import plotly.express as px
import streamlit as st

import analysis
import auth
import data_loader as dl
import logic as L

st.set_page_config(page_title="Khwezi Mining Monitor", page_icon="⛏️", layout="wide")

NAVY, AMBER, GREEN, RED, BLUE = "#3E81D8", "#F5A623", "#2E9E5B", "#D62839", "#1F6FEB"
STATUS_COL = {"Normal": GREEN, "Warning": AMBER, "Critical": RED, "Low": GREEN, "Medium": "#F2C94C", "High": "#E67E22"}

st.markdown(f"""<style>
[data-testid="stSidebar"] {{background: linear-gradient(180deg,{NAVY},#14325C);}}
[data-testid="stSidebar"] * {{color:#fff !important;}}
.banner {{background:linear-gradient(90deg,{NAVY},{BLUE});padding:18px 26px;border-radius:12px;color:#fff;margin-bottom:18px;border-left:8px solid {AMBER};}}
.banner h2 {{margin:0;color:#fff;}} .banner p {{margin:2px 0 0;opacity:.85;}}
.card {{background:#fff;border-radius:12px;padding:14px 16px;box-shadow:0 2px 8px rgba(0,0,0,.10);border-top:5px solid var(--c);margin-bottom:12px;}}
.card .v {{font-size:1.9rem;font-weight:700;color:var(--c);}} .card .l {{font-size:.85rem;color:#555;}}
.badge {{display:inline-block;padding:2px 10px;border-radius:12px;color:#fff;font-size:.8rem;font-weight:600;}}
.foot {{text-align:center;color:#777;font-size:.78rem;margin-top:30px;border-top:1px solid #ddd;padding-top:8px;}}
</style>""", unsafe_allow_html=True)


# ---------- helpers ----------
def banner(title, sub):
    st.markdown(f'<div class="banner"><h2>{title}</h2><p>{sub}</p></div>', unsafe_allow_html=True)


def cards(items, cols=4):
    palette = [BLUE, AMBER, GREEN, RED, "#8E44AD", "#16A5A5"]
    cs = st.columns(cols)
    for i, (label, value) in enumerate(items.items()):
        cs[i % cols].markdown(f'<div class="card" style="--c:{palette[i % len(palette)]}"><div class="v">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)


def show(df, colour_cols=()):
    """Show a table; colour the cells of status columns."""
    if df.empty:
        st.info("No records match the current selection."); return
    sty = df.style
    for c in colour_cols:
        if c in df.columns:
            f = lambda v: f"background-color:{STATUS_COL.get(str(v).title(), 'white')};color:white;font-weight:600" if str(v).title() in STATUS_COL else ""
            sty = (sty.map if hasattr(sty, "map") else sty.applymap)(f, subset=[c])
    st.dataframe(sty, use_container_width=True, hide_index=True)


def reload():
    st.session_state["d"] = dl.load_all()


def allowed(function):
    return auth.has_access(st.session_state["d"]["perms"], st.session_state["user"]["Role"], function)


# ---------- login ----------
def login_page():
    banner("⛏️ Khwezi Mining", "Health, Safety and Equipment Monitoring Application — secure login")
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid, st.form("login"):
        st.subheader("Sign in")
        u = st.text_input("Username"); p = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if not u or not p:
                st.warning("Please enter both username and password.")
            else:
                user = auth.authenticate(st.session_state["d"]["users"], u, p)
                if user is None:
                    st.error("Invalid credentials or inactive account.")
                else:
                    st.session_state["user"] = user; st.rerun()


# ---------- pages ----------
def page_dashboard(d):
    banner("📊 Mining Monitoring Dashboard", "Key performance indicators across safety and equipment")
    cards(L.kpis(d))
    eq, inc = d["equipment"], d["incidents"]
    c1, c2 = st.columns(2)
    m = inc.groupby(inc["Date"].dt.strftime("%Y-%m")).size().reset_index(name="Incidents").rename(columns={"Date": "Month"})
    c1.plotly_chart(px.line(m, x="Month", y="Incidents", markers=True, title="Incident trend by month", color_discrete_sequence=[BLUE]), use_container_width=True)
    s = eq["Overall_Status"].value_counts().rename_axis("Status").reset_index(name="Equipment")
    c2.plotly_chart(px.pie(s, names="Status", values="Equipment", hole=.5, title="Equipment status", color="Status", color_discrete_map=STATUS_COL), use_container_width=True)
    c3, c4 = st.columns(2)
    dpt = inc["Department"].value_counts().rename_axis("Department").reset_index(name="Incidents")
    c3.plotly_chart(px.bar(dpt, x="Department", y="Incidents", color="Department", title="Incidents by department", color_discrete_sequence=analysis.COLORS), use_container_width=True)
    rk = L.risk_table(d["risks"])["Classification"].value_counts().rename_axis("Class").reset_index(name="Risks")
    c4.plotly_chart(px.bar(rk, x="Class", y="Risks", color="Class", title="Risk register classification", color_discrete_map=STATUS_COL | {"Critical": RED}), use_container_width=True)
    a = L.all_alerts(eq)
    st.subheader(f"🚨 Latest critical alerts ({(a['Level'] == 'CRITICAL').sum()} active)")
    show(a[a["Level"] == "CRITICAL"].head(8), ["Level"])


def page_workers(d):
    banner("👷 Worker Health and Safety", "PPE compliance, fatigue, training and risk level")
    w = d["workers"]
    f1, f2, f3 = st.columns(3)
    dep = f1.multiselect("Department", sorted(w["Department"].unique())); sh = f2.multiselect("Shift", sorted(w["Shift"].unique())); rl = f3.multiselect("Risk level", ["Low", "Medium", "High", "Critical"])
    if dep: w = w[w["Department"].isin(dep)]
    if sh: w = w[w["Shift"].isin(sh)]
    if rl: w = w[w["Risk_Level"].isin(rl)]
    cards({"Workers": len(w), "PPE compliant %": round((w["PPE_Compliant"] == "Yes").mean() * 100, 1) if len(w) else 0, "High fatigue (7+)": int((w["Fatigue_Level"] >= 7).sum()), "Training expired": int((w["Safety_Training_Status"] == "Expired").sum())})
    show(w.drop(columns=["Safety_Training_Expiry_Date"]), ["Risk_Level"])
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(w, names="Risk_Level", title="Workers by risk level", color="Risk_Level", color_discrete_map=STATUS_COL), use_container_width=True)
    c2.plotly_chart(px.box(w, x="Department", y="Fatigue_Level", color="Department", title="Fatigue level by department", color_discrete_sequence=analysis.COLORS), use_container_width=True)
    st.subheader("⚠️ Unsafe conditions detected")
    show(L.worker_alerts(w))


def page_incidents(d):
    banner("🦺 Safety Incident Database", "Add, search, filter and analyse incidents")
    inc = d["incidents"]
    tab1, tab2, tab3 = st.tabs(["View / Search", "Add incident", "Trends"])
    with tab1:
        a, b, c, e = st.columns(4)
        q = a.text_input("Search (ID, cause, type...)"); dep = b.multiselect("Department", sorted(inc["Department"].unique()))
        sev = c.multiselect("Severity", ["Low", "Medium", "High", "Critical"]); stt = e.multiselect("Status", sorted(inc["Incident_Status"].unique()))
        r = inc.copy()
        if q: r = r[r.astype(str).apply(lambda s: s.str.contains(q, case=False)).any(axis=1)]
        if dep: r = r[r["Department"].isin(dep)]
        if sev: r = r[r["Severity"].isin(sev)]
        if stt: r = r[r["Incident_Status"].isin(stt)]
        cards({"Incidents shown": len(r), "Lost-time injuries": int((r["Lost_Time_Injury"] == "Yes").sum()), "High/Critical": int(r["Severity"].isin(["High", "Critical"]).sum()), "Not closed": int((r["Incident_Status"] != "Closed").sum())})
        show(r.assign(Date=r["Date"].dt.strftime("%Y-%m-%d")), ["Severity"])
    with tab2:
        with st.form("add_inc", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            dt = c1.date_input("Date"); tm = c2.time_input("Time"); wid = c3.selectbox("Worker ID", d["workers"]["Worker_ID"])
            loc = c1.selectbox("Location", sorted(inc["Location"].unique())); dep = c2.selectbox("Department", sorted(inc["Department"].unique())); typ = c3.selectbox("Incident type", sorted(inc["Incident_Type"].unique()))
            sev = c1.selectbox("Severity", ["Low", "Medium", "High", "Critical"]); injury = c2.selectbox("Injury status", sorted(inc["Injury_Status"].unique())); days = c3.number_input("Lost days", 0, 365, 0)
            cause = c1.selectbox("Cause", sorted(inc["Cause"].unique())); eqid = c2.selectbox("Equipment ID (optional)", [""] + sorted(d["equipment"]["Equipment_ID"])); stt = c3.selectbox("Status", ["Open", "Under Investigation", "Closed"])
            action = st.text_input("Corrective action")
            if st.form_submit_button("Save incident"):
                if not action.strip(): st.error("Corrective action is required.")
                elif injury == "Lost Time Injury" and days == 0: st.error("A lost-time injury must have at least 1 lost day.")
                elif injury != "Lost Time Injury" and days > 0: st.error("Lost days only apply to lost-time injuries.")
                else:
                    shift = "Day" if 6 <= tm.hour < 18 else "Night"
                    new = {"Incident_ID": f"INC-2026-{len(inc) + 1:04d}", "Date": pd.Timestamp(dt), "Time": tm.strftime("%H:%M"), "Shift": shift, "Location": loc, "Department": dep, "Incident_Type": typ, "Severity": sev, "Injury_Status": injury, "Lost_Time_Injury": "Yes" if injury == "Lost Time Injury" else "No", "Lost_Days": int(days), "Cause": cause, "Corrective_Action": action, "Incident_Status": stt, "Worker_ID": wid, "Equipment_ID": eqid or None}
                    out = pd.concat([inc, pd.DataFrame([new])], ignore_index=True)
                    dl.save_csv(out, "safety_incidents.csv"); reload()
                    st.success(f"Incident {new['Incident_ID']} saved."); st.rerun()
    with tab3:
        m = inc.groupby([inc["Date"].dt.strftime("%Y-%m"), "Severity"]).size().reset_index(name="Incidents").rename(columns={"Date": "Month"})
        st.plotly_chart(px.bar(m, x="Month", y="Incidents", color="Severity", title="Monthly incidents by severity", color_discrete_map={"Low": GREEN, "Medium": "#F2C94C", "High": "#E67E22", "Critical": RED}), use_container_width=True)
        t = inc["Incident_Type"].value_counts().reset_index(); t.columns = ["Incident_Type", "Count"]
        st.plotly_chart(px.bar(t, x="Count", y="Incident_Type", orientation="h", title="Incidents by type", color="Count", color_continuous_scale="Oranges"), use_container_width=True)


def live_equipment(eq):
    """Recalculate condition from temperature and vibration using the logic module."""
    e = eq.copy()
    e["Temp status"] = e["Temperature_C"].map(L.classify_temperature); e["Vib status"] = e["Vibration_mm_s"].map(L.classify_vibration)
    e["Message"] = [L.equipment_message(t, v) for t, v in zip(e["Temperature_C"], e["Vibration_mm_s"])]
    return e


def page_equipment(d):
    banner("🚜 Equipment Condition Monitoring", "Temperature and vibration against prototype thresholds")
    e = live_equipment(d["equipment"])
    a, b = st.columns(2)
    typ = a.multiselect("Equipment type", sorted(e["Equipment_Type"].unique())); stt = b.multiselect("Overall status", ["Normal", "Warning", "Critical"])
    if typ: e = e[e["Equipment_Type"].isin(typ)]
    if stt: e = e[e["Overall_Status"].isin(stt)]
    cards({"Equipment shown": len(e), "Critical": int((e["Overall_Status"] == "Critical").sum()), "Warning": int((e["Overall_Status"] == "Warning").sum()), "Avg availability %": round(e["Availability_Percent"].mean(), 1) if len(e) else 0})
    show(e[["Equipment_ID", "Equipment_Type", "Manufacturer", "Operating_Hours", "Temperature_C", "Temp status", "Vibration_mm_s", "Vib status", "Availability_Percent", "Overall_Status"]], ["Temp status", "Vib status", "Overall_Status"])
    st.subheader("Trend for one machine")
    eid = st.selectbox("Equipment ID", sorted(d["equipment"]["Equipment_ID"]))
    r = d["readings"].query("Equipment_ID == @eid"); row = d["equipment"].query("Equipment_ID == @eid").iloc[0]
    st.info(L.equipment_message(row["Temperature_C"], row["Vibration_mm_s"]))
    c1, c2 = st.columns(2)
    f1 = px.line(r, x="Date", y="Temperature_C", title="Temperature (C)", markers=True, color_discrete_sequence=[RED]); f1.add_hline(y=L.TEMP_WARN, line_dash="dash", line_color=AMBER); f1.add_hline(y=L.TEMP_CRIT, line_dash="dash", line_color=RED)
    f2 = px.line(r, x="Date", y="Vibration_mm_s", title="Vibration (mm/s)", markers=True, color_discrete_sequence=[BLUE]); f2.add_hline(y=L.VIB_WARN, line_dash="dash", line_color=AMBER); f2.add_hline(y=L.VIB_CRIT, line_dash="dash", line_color=RED)
    c1.plotly_chart(f1, use_container_width=True); c2.plotly_chart(f2, use_container_width=True)
    st.caption("Dashed lines: warning (amber) and critical (red) prototype thresholds.")


def page_maintenance(d):
    banner("🔧 Equipment Maintenance Monitoring", "Availability = Operating / (Operating + Downtime) x 100")
    e = d["equipment"].copy(); e["Availability (calc) %"] = [L.calculate_availability(o, dn) for o, dn in zip(e["Period_Operating_Hours"], e["Downtime_Hours"])]
    cards({"Due soon (14 days)": int(e["Due_Soon"].sum()), "Overdue": int(e["Overdue"].sum()), "Under maintenance": int(e["Under_Maintenance"].sum()), "Excessive downtime": int(e["Excessive_Downtime"].sum()), "Repeated alerts": int(e["Repeated_Alerts"].sum()), "Low availability": int(e["Low_Availability"].sum())}, 3)
    cols = ["Equipment_ID", "Equipment_Type", "Department", "Next_Maintenance_Date", "Days_To_Next_Maintenance", "Availability (calc) %", "Downtime_Hours", "Priority_Tier"]
    t = st.tabs(["Due soon", "Overdue", "Under maintenance", "Excessive downtime", "Repeated alerts", "Low availability"])
    for tab, flt in zip(t, ["Due_Soon", "Overdue", "Under_Maintenance", "Excessive_Downtime", "Repeated_Alerts", "Low_Availability"]):
        with tab: show(e[e[flt]][cols].assign(Next_Maintenance_Date=lambda x: x["Next_Maintenance_Date"].dt.strftime("%Y-%m-%d")))
    g = e.groupby("Equipment_Type")["Availability (calc) %"].mean().round(1).reset_index()
    st.plotly_chart(px.bar(g, x="Equipment_Type", y="Availability (calc) %", color="Equipment_Type", title="Average availability by equipment type", color_discrete_sequence=analysis.COLORS, text_auto=True), use_container_width=True)


def page_risk(d):
    banner("⚖️ Risk Assessment", "Risk Score = Likelihood x Consequence (1-5 scale)")
    rt = L.risk_table(d["risks"])
    for _, r in rt[rt["Classification"].isin(["High", "Critical"])].head(5).iterrows():
        (st.error if r["Classification"] == "Critical" else st.warning)(f"{r['Risk_ID']} - {r['Hazard_Category']} ({r['Department']}): {L.risk_warning(r['Risk_Score'])}")
    show(rt.drop(columns=["Risk_Description"]).assign(Next_Review_Date=rt["Next_Review_Date"].dt.strftime("%Y-%m-%d")), ["Classification"])
    st.subheader("Risk calculator")
    a, b = st.columns(2); lk = a.slider("Likelihood", 1, 5, 3); cq = b.slider("Consequence", 1, 5, 3)
    sc = L.risk_score(lk, cq); cl = L.risk_class(sc)
    st.markdown(f'Score **{sc}** → <span class="badge" style="background:{STATUS_COL.get(cl, RED)}">{cl}</span>', unsafe_allow_html=True)
    if L.risk_warning(sc): st.error(L.risk_warning(sc))
    mat = pd.DataFrame([[l * c for c in range(1, 6)] for l in range(5, 0, -1)], index=[f"L{l}" for l in range(5, 0, -1)], columns=[f"C{c}" for c in range(1, 6)])
    st.plotly_chart(px.imshow(mat, text_auto=True, color_continuous_scale=["#2E9E5B", "#F2C94C", "#E67E22", "#D62839"], title="Risk matrix"), use_container_width=True)


def page_alerts(d):
    banner("🚨 Alerts and Notifications", "Generated automatically from the predefined conditions")
    if allowed("Equipment data"):
        a = L.all_alerts(d["equipment"]); lvl = st.radio("Level", ["All", "CRITICAL", "WARNING"], horizontal=True)
        if lvl != "All": a = a[a["Level"] == lvl]
        show(a, ["Level"])
        if len(a):
            st.markdown("**Alert preview (Figure 1 format)**"); st.code(L.format_alert(a.iloc[st.number_input("Alert number", 1, len(a), 1) - 1]), language="text")
    if allowed("Worker safety data"):
        st.subheader("Worker safety warnings"); show(L.worker_alerts(d["workers"]))


def page_analysis(d):
    banner("🔍 Interactive Data Analysis", "Answer mining engineering questions from the data")
    inc = d["incidents"]; lo, hi = inc["Date"].min().date(), inc["Date"].max().date()
    rng = st.date_input("Incident period", (lo, hi), min_value=lo, max_value=hi)
    if len(rng) == 2: inc = inc[(inc["Date"] >= pd.Timestamp(rng[0])) & (inc["Date"] <= pd.Timestamp(rng[1]))]
    ok = {q: v for q, v in analysis.QUESTIONS.items() if v[0] == "both" and allowed("Equipment data") and allowed("Worker safety data") or v[0] == "equipment" and allowed("Equipment data") or v[0] == "safety" and allowed("Safety incidents")}
    q = st.selectbox("Choose a question", list(ok))
    table, fig, text = ok[q][1](d, inc)
    st.success(text)
    if fig is not None: st.plotly_chart(fig, use_container_width=True)
    show(table)


def page_reports(d):
    banner("📄 Reports", "Download data and summaries as CSV")
    inc = d["incidents"]
    if allowed("Safety incidents"):
        st.download_button("⬇ Incident summary (by department & severity)", inc.groupby(["Department", "Severity"]).size().reset_index(name="Incidents").to_csv(index=False), "incident_summary.csv")
    if allowed("Equipment data"):
        st.download_button("⬇ Equipment alerts", L.all_alerts(d["equipment"]).to_csv(index=False), "equipment_alerts.csv")
        st.download_button("⬇ Maintenance priority list", d["equipment"].sort_values("Priority_Score", ascending=False)[["Equipment_ID", "Equipment_Type", "Maintenance_Status", "Priority_Score", "Priority_Tier", "Recommended_Action"]].to_csv(index=False), "maintenance_priority.csv")
    if allowed("Risk assessment"):
        st.download_button("⬇ Risk register with scores", L.risk_table(d["risks"]).to_csv(index=False), "risk_register_scored.csv")
    if allowed("Worker safety data"):
        st.download_button("⬇ Worker safety warnings", L.worker_alerts(d["workers"]).to_csv(index=False), "worker_warnings.csv")
    st.subheader("Management recommendations")
    k = L.kpis(d); recs = [f"Inspect the **{k['Critical equipment']}** critical machines immediately.", f"Schedule the **{k['Overdue maintenance']}** overdue maintenance jobs.", f"Raise PPE compliance (currently **{k['PPE compliance %']}%**).", f"Close the **{k['Open incidents']}** open or under-investigation incidents."]
    for r in recs: st.markdown(f"- {r}")


def page_users(d):
    banner("👥 Manage Users", "Administrator only")
    u = d["users"]; show(u.drop(columns=["Salt", "Password_Hash"]))
    with st.form("new_user", clear_on_submit=True):
        c1, c2, c3 = st.columns(3); un = c1.text_input("Username"); nm = c2.text_input("Full name"); pw = c3.text_input("Password", type="password")
        role = c1.selectbox("Role", ["Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"]); dp = c2.text_input("Department"); em = c3.text_input("Email")
        if st.form_submit_button("Add user"):
            if not (un and nm and pw and em): st.error("All fields are required.")
            elif len(pw) < 8: st.error("Password must be at least 8 characters.")
            elif un.lower() in u["Username"].str.lower().values: st.error("Username already exists.")
            else:
                s = auth.new_salt()
                row = {"User_ID": f"U{len(u) + 1:03d}", "Username": un, "Full_Name": nm, "Role": role, "Department": dp, "Email": em, "Salt": s, "Password_Hash": auth.hash_password(pw, s), "Active": "Yes"}
                dl.save_csv(pd.concat([u, pd.DataFrame([row])], ignore_index=True), "users.csv"); reload(); st.success("User added."); st.rerun()
    c1, c2 = st.columns(2); who = c1.selectbox("Activate / deactivate", u["Username"]); act = c2.radio("Set account", ["Yes", "No"], horizontal=True)
    if st.button("Update account"):
        if who == st.session_state["user"]["Username"]: st.error("You cannot change your own account.")
        else:
            u.loc[u["Username"] == who, "Active"] = act; dl.save_csv(u, "users.csv"); reload(); st.success("Updated."); st.rerun()


# ---------- main ----------
PAGES = {"📊 Dashboard": ("View dashboard", page_dashboard), "👷 Worker Safety": ("Worker safety data", page_workers), "🦺 Safety Incidents": ("Safety incidents", page_incidents),
         "🚜 Equipment": ("Equipment data", page_equipment), "🔧 Maintenance": ("Maintenance data", page_maintenance), "⚖️ Risk Assessment": ("Risk assessment", page_risk),
         "🚨 Alerts": ("View dashboard", page_alerts), "🔍 Data Analysis": ("View dashboard", page_analysis), "📄 Reports": ("Generate reports", page_reports), "👥 Manage Users": ("Manage users", page_users)}


def main():
    if "d" not in st.session_state: reload()
    if "user" not in st.session_state: login_page(); return
    user, d = st.session_state["user"], st.session_state["d"]
    menu = [p for p, (fn, _) in PAGES.items() if auth.has_access(d["perms"], user["Role"], fn)]
    with st.sidebar:
        st.markdown("## ⛏️ Khwezi Mining")
        st.markdown(f"**{user['Full_Name']}**  \n{user['Role']}")
        page = st.radio("Navigation", menu, label_visibility="collapsed")
        if st.button("Logout", use_container_width=True): st.session_state.pop("user"); st.rerun()
    try:
        PAGES[page][1](d)
    except Exception as ex:  # error prevention: show a message instead of crashing the app
        st.error(f"Something went wrong on this page: {ex}")
    st.markdown('<div class="foot">Educational prototype - thresholds are not real manufacturer or mine safety limits. MINN2020A, University of the Witwatersrand.</div>', unsafe_allow_html=True)


main()
