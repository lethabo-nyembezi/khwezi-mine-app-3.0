"""analysis.py - interactive business questions (Appendix A). Each returns (table, figure, answer text)."""
import pandas as pd
import plotly.express as px
import logic as L

COLORS = ["#1F6FEB", "#F5A623", "#2E9E5B", "#D62839", "#8E44AD", "#16A5A5", "#E67E22", "#34495E"]


def _bar(df, x, y, title, color=None):
    fig = px.bar(df, x=x, y=y, title=title, color=color or x, color_discrete_sequence=COLORS, text_auto=True)
    fig.update_layout(showlegend=False, plot_bgcolor="white", title_font_size=16)
    return fig


def _count(inc, col, title):
    t = inc[col].value_counts().rename_axis(col).reset_index(name="Incidents")
    return t, _bar(t, col, "Incidents", title), f"**{t.iloc[0][col]}** has the most incidents ({t.iloc[0]['Incidents']})."


def _top(eq, col, title, asc=False, n=10):
    t = eq.sort_values(col, ascending=asc).head(n)[["Equipment_ID", "Equipment_Type", "Department", col]]
    return t, _bar(t, "Equipment_ID", col, title, "Equipment_Type"), f"**{t.iloc[0]['Equipment_ID']}** ({t.iloc[0]['Equipment_Type']}) is first with {t.iloc[0][col]}."


def q_causes(d, inc):
    t = inc["Cause"].value_counts().head(10).rename_axis("Cause").reset_index(name="Incidents")
    return t, _bar(t, "Cause", "Incidents", "Top 10 causes of incidents"), f"Most common cause: **{t.iloc[0]['Cause']}** ({t.iloc[0]['Incidents']} incidents)."


def q_ppe(d, inc):
    w = d["workers"]; t = w.groupby("Department")["PPE_Compliant"].apply(lambda s: round((s == "Yes").mean() * 100, 1)).reset_index(name="PPE compliant %")
    return t, _bar(t, "Department", "PPE compliant %", "PPE compliance by department"), f"Overall PPE compliance is **{round((w['PPE_Compliant'] == 'Yes').mean() * 100, 1)}%**."


def q_nearmiss(d, inc):
    t = inc[inc["Injury_Status"] == "Near Miss"].groupby("Department").size().reset_index(name="Near misses")
    return t, _bar(t, "Department", "Near misses", "Near misses by department"), f"**{int(t['Near misses'].sum())}** near misses recorded."


def q_highcrit(d, inc):
    h = inc[inc["Severity"].isin(["High", "Critical"])]
    t = h.groupby(["Department", "Severity"]).size().reset_index(name="Incidents")
    return t, px.bar(t, x="Department", y="Incidents", color="Severity", barmode="group", title="High / Critical incidents", color_discrete_map={"High": "#E67E22", "Critical": "#D62839"}), f"**{len(h)}** incidents are High or Critical."


def q_shift(d, inc):
    t = inc.groupby(["Shift", "Severity"]).size().reset_index(name="Incidents")
    tot = inc["Shift"].value_counts()
    return t, px.bar(t, x="Shift", y="Incidents", color="Severity", title="Incidents by shift and severity"), f"Night: **{tot.get('Night', 0)}** vs Day: **{tot.get('Day', 0)}** incidents."


def q_dept_risk(d, inc):
    eq, w = d["equipment"], d["workers"]
    a = w.assign(HR=w["Risk_Level"].isin(["High", "Critical"])).groupby("Department")["HR"].sum().rename("High-risk workers")
    b = eq.groupby("Department")["Downtime_Hours"].sum().round(0).rename("Total downtime (h)")
    t = pd.concat([a, b], axis=1).reset_index().rename(columns={"index": "Department"})
    fig = px.scatter(t, x="High-risk workers", y="Total downtime (h)", size="Total downtime (h)", color="Department", text="Department", title="Safety risk vs equipment downtime", color_discrete_sequence=COLORS)
    return t, fig, "Departments at the top-right have **both** high safety risk and high equipment downtime."


def q_normal(d, inc):
    t = d["equipment"]["Overall_Status"].value_counts().rename_axis("Status").reset_index(name="Equipment")
    fig = px.pie(t, names="Status", values="Equipment", hole=0.5, title="Equipment status", color="Status", color_discrete_map={"Normal": "#2E9E5B", "Warning": "#F5A623", "Critical": "#D62839"})
    return t, fig, f"**{round((d['equipment']['Overall_Status'] == 'Normal').mean() * 100, 1)}%** of equipment is operating normally."


def q_critical(d, inc):
    a = L.all_alerts(d["equipment"]); c = a[a["Level"] == "CRITICAL"]
    return c, None, f"**{len(c)}** critical alerts are currently active."


def q_overdue(d, inc):
    t = d["equipment"].query("Overdue").sort_values("Days_Overdue", ascending=False)[["Equipment_ID", "Equipment_Type", "Department", "Days_Overdue"]]
    return t, _bar(t.head(15), "Equipment_ID", "Days_Overdue", "Most overdue equipment", "Equipment_Type"), f"**{len(t)}** machines are overdue for maintenance."


def q_type_down(d, inc):
    t = d["equipment"].groupby("Equipment_Type")["Downtime_Hours"].sum().round(0).sort_values(ascending=False).reset_index()
    return t, _bar(t, "Equipment_Type", "Downtime_Hours", "Downtime by equipment type"), f"**{t.iloc[0]['Equipment_Type']}** has the highest total downtime."


def q_inspect(d, inc):
    t = d["equipment"].query("Needs_Inspection")[["Equipment_ID", "Equipment_Type", "Temperature_C", "Vibration_mm_s", "Status_Message"]]
    return t, None, f"**{len(t)}** machines need immediate inspection."


def q_priority(d, inc):
    return _top(d["equipment"], "Priority_Score", "Maintenance priority (top 10)")


def q_avail(d, inc):
    t = d["equipment"].groupby("Equipment_Type")["Availability_Percent"].mean().round(1).reset_index()
    return t, _bar(t, "Equipment_Type", "Availability_Percent", "Average availability by type"), f"Average fleet availability is **{round(d['equipment']['Availability_Percent'].mean(), 1)}%**."


QUESTIONS = {
    "How many incidents occurred in the selected period?": ("safety", lambda d, i: (i.groupby(i["Date"].dt.strftime("%Y-%m")).size().reset_index(name="Incidents").rename(columns={"Date": "Month"}), None, f"**{len(i)}** incidents in the selected period.")),
    "Which department has the highest number of incidents?": ("safety", lambda d, i: _count(i, "Department", "Incidents by department")),
    "Which shift records the most incidents?": ("safety", lambda d, i: _count(i, "Shift", "Incidents by shift")),
    "What percentage of workers comply with PPE?": ("safety", q_ppe),
    "How many near misses have been recorded?": ("safety", q_nearmiss),
    "Which incident types occur most frequently?": ("safety", lambda d, i: _count(i, "Incident_Type", "Incident types")),
    "How many incidents are High or Critical?": ("safety", q_highcrit),
    "Is there a difference between day and night shifts?": ("safety", q_shift),
    "What are the most common causes of incidents?": ("safety", q_causes),
    "Which equipment has the highest downtime?": ("equipment", lambda d, i: _top(d["equipment"], "Downtime_Hours", "Highest downtime (h)")),
    "Which equipment has the lowest availability?": ("equipment", lambda d, i: _top(d["equipment"], "Availability_Percent", "Lowest availability (%)", asc=True)),
    "Which equipment has the highest vibration?": ("equipment", lambda d, i: _top(d["equipment"], "Vibration_mm_s", "Highest vibration (mm/s)")),
    "Which equipment has the highest temperature?": ("equipment", lambda d, i: _top(d["equipment"], "Temperature_C", "Highest temperature (C)")),
    "Which equipment has generated the most alerts?": ("equipment", lambda d, i: _top(d["equipment"], "Alert_Count", "Most alerts")),
    "Which equipment is overdue for maintenance?": ("equipment", q_overdue),
    "What is the average equipment availability?": ("equipment", q_avail),
    "Which equipment type has the highest downtime?": ("equipment", q_type_down),
    "Which equipment requires immediate inspection?": ("equipment", q_inspect),
    "Which equipment should receive maintenance priority?": ("equipment", q_priority),
    "What percentage of equipment is operating normally?": ("equipment", q_normal),
    "How many critical alerts are currently active?": ("equipment", q_critical),
    "Which departments have both high safety risk and high downtime?": ("both", q_dept_risk),
}
