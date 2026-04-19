import pandas as pd
import streamlit as st
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "jobs.csv"

STATUS_OPTIONS = ["not started", "applied", "interviewing", "rejected", "offer"]
STATUS_COLOURS = {
    "not started": "🔵",
    "applied":     "🟡",
    "interviewing":"🟠",
    "rejected":    "🔴",
    "offer":       "🟢",
    "":            "⚪",
}

TYPE_OPTIONS = ["computational", "clinical", "biological", "bioinformatics"]
FIT_OPTIONS  = ["high", "medium", "low"]
FIT_COLOURS  = {"high": "🟢", "medium": "🟡", "low": "🔴", "": "⚪"}

st.set_page_config(page_title="PhD Job Tracker", layout="wide")


# ── Load data once ─────────────────────────────────────────────────────────────
# Never re-read from CSV mid-session — edits live in session_state.df
if "df" not in st.session_state:
    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce")
    st.session_state.df = df

if "selected_idx" not in st.session_state:
    st.session_state.selected_idx = None


def save_edit(idx: int, new_status: str, new_notes: str, new_type: str, new_fit: str) -> None:
    st.session_state.df.at[idx, "application_status"] = new_status
    st.session_state.df.at[idx, "notes"] = new_notes
    st.session_state.df.at[idx, "type"] = new_type or ""
    st.session_state.df.at[idx, "fit"] = new_fit or ""
    out = st.session_state.df.copy()
    out["deadline"] = out["deadline"].dt.strftime("%Y-%m-%d")
    out.to_csv(CSV_PATH, index=False)


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("PhD Job Tracker")

    if st.button("↻ Reload from CSV", use_container_width=True):
        df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
        df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce")
        st.session_state.df = df
        st.session_state.selected_idx = None
        st.rerun()

    st.divider()
    st.subheader("Filters")

    status_filter = st.multiselect(
        "Application status",
        options=STATUS_OPTIONS,
        default=[],
        placeholder="All statuses",
        key="status_filter",
    )
    type_filter = st.multiselect(
        "Job type",
        options=TYPE_OPTIONS,
        default=[],
        placeholder="All types",
        key="type_filter",
    )
    fit_filter = st.multiselect(
        "Fit",
        options=FIT_OPTIONS,
        default=[],
        placeholder="All fits",
        key="fit_filter",
    )
    hide_expired = st.toggle("Hide expired deadlines", value=False, key="hide_expired")

    st.divider()
    st.subheader("Summary")
    df_all = st.session_state.df
    total = len(df_all)
    st.caption(f"{total} saved jobs")
    for s in STATUS_OPTIONS:
        n = (df_all["application_status"] == s).sum()
        st.write(f"{STATUS_COLOURS[s]} {s}: **{n}**")
    unset = (df_all["application_status"] == "").sum()
    if unset:
        st.write(f"⚪ unset: **{unset}**")


# ── Filter view ─────────────────────────────────────────────────────────────────
view = st.session_state.df.copy()
if status_filter:
    view = view[view["application_status"].isin(status_filter)]
if type_filter:
    view = view[view["type"].isin(type_filter)]
if fit_filter:
    view = view[view["fit"].isin(fit_filter)]
if hide_expired:
    view = view[view["deadline"] >= pd.Timestamp.today().normalize()]

# ── Overview table ──────────────────────────────────────────────────────────────
st.subheader(f"Jobs ({len(view)})")

TABLE_COLS = ["title", "institution", "city", "deadline", "type", "fit", "application_status"]
display = view[TABLE_COLS].copy()
display["deadline"] = display["deadline"].dt.strftime("%Y-%m-%d")
display[""] = display["application_status"].map(STATUS_COLOURS)
display["🎯"] = display["fit"].map(FIT_COLOURS)
display = display[["", "title", "institution", "city", "deadline", "type", "🎯", "application_status"]]

event = st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="job_table",
    column_config={
        "":                   st.column_config.TextColumn("", width="small"),
        "title":              st.column_config.TextColumn("Title", width="large"),
        "institution":        st.column_config.TextColumn("Institution"),
        "city":               st.column_config.TextColumn("City", width="small"),
        "deadline":           st.column_config.TextColumn("Deadline", width="small"),
        "type":               st.column_config.TextColumn("Type", width="small"),
        "🎯":                 st.column_config.TextColumn("Fit", width="small"),
        "application_status": st.column_config.TextColumn("Status", width="small"),
    },
)

# Map selected display-row → original DataFrame index
sel_rows = event.selection.rows
if sel_rows:
    st.session_state.selected_idx = view.index[sel_rows[0]]

# ── Detail panel ─────────────────────────────────────────────────────────────────
idx = st.session_state.selected_idx
if idx is not None and idx in st.session_state.df.index:
    job = st.session_state.df.loc[idx]

    st.divider()

    # Header
    st.markdown(f"## {job['title']}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Institution", job["institution"])
    c2.metric("Location", f"{job['city']}, {job['country']}")
    c3.metric("Deadline", pd.to_datetime(job["deadline"]).strftime("%Y-%m-%d"))
    salary = (f"€{job['salary_min_eur']}–€{job['salary_max_eur']}/mo"
              if job["salary_min_eur"] else "—")
    c4.metric("Salary", salary)

    st.caption(
        f"[View on AcademicTransfer ↗]({job['url']})  ·  "
        f"{job['weekly_hours']}  ·  {job['contract_duration']}"
    )

    # Edit status, type, notes
    # Widget keys include idx so Streamlit resets them when a different row is selected
    st.markdown("#### Track application")
    ec1, ec2, ec3, ec4 = st.columns([1, 1, 1, 2])
    with ec1:
        current_status = job["application_status"]
        safe_status_idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
        new_status = st.selectbox(
            "Status",
            options=STATUS_OPTIONS,
            index=safe_status_idx,
            key=f"sel_status_{idx}",
        )
    with ec2:
        current_type = job["type"]
        type_index = TYPE_OPTIONS.index(current_type) if current_type in TYPE_OPTIONS else None
        new_type = st.selectbox(
            "Type",
            options=TYPE_OPTIONS,
            index=type_index,
            placeholder="Select type…",
            key=f"sel_type_{idx}",
        )
    with ec3:
        current_fit = job["fit"]
        fit_index = FIT_OPTIONS.index(current_fit) if current_fit in FIT_OPTIONS else None
        new_fit = st.selectbox(
            "Fit",
            options=FIT_OPTIONS,
            index=fit_index,
            placeholder="Select fit…",
            key=f"sel_fit_{idx}",
        )
    with ec4:
        new_notes = st.text_area(
            "Notes",
            value=job["notes"],
            height=80,
            key=f"txt_notes_{idx}",
        )

    if st.button("Save", type="primary", key=f"btn_save_{idx}"):
        save_edit(idx, new_status, new_notes, new_type, new_fit)
        st.success("Saved to jobs.csv")

    st.divider()

    # Content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Job Description", "Requirements", "Conditions of Employment",
        "Employer", "Department", "Contact",
    ])

    def md(text: str) -> None:
        # Single \n is ignored in Markdown; double \n creates a paragraph break
        st.markdown(text.replace("\n", "\n\n") if text else "—")

    with tab1:
        md(job["job_description"])
    with tab2:
        md(job["requirements"])
    with tab3:
        md(job["conditions_of_employment"])
    with tab4:
        md(job["employer"])
    with tab5:
        md(job["department"])
    with tab6:
        if job["contact_email"]:
            st.markdown(f"**{job['contact_name']}**")
            st.markdown(f"📧 {job['contact_email']}")
        else:
            st.write("No contact information available.")
else:
    st.info("Select a row above to view job details.")
