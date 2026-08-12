"""
modules/tabs/transfers_tab.py
Transfers tab — Google Sheets as primary live source with auto-refresh,
Excel fallback, all charts update from whatever source is active.
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, datetime, timedelta
import random

from modules.database import get_transfers_sheet_url, set_transfers_sheet_url

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
TRANSFERS_FILE = os.path.join(DATA_DIR, "transfers.xlsx")


# ── Google Sheets helpers ─────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _fetch_sheet(sheet_url: str) -> pd.DataFrame:
    """Download a public Google Sheet as CSV and return a DataFrame."""
    try:
        if "/d/" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            gid = "0"
            if "gid=" in sheet_url:
                gid = sheet_url.split("gid=")[1].split("&")[0].split("#")[0]
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                f"/export?format=csv&gid={gid}"
            )
        else:
            csv_url = sheet_url
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return pd.DataFrame()


def _push_to_sheets(df: pd.DataFrame, url: str):
    """Write DataFrame back to a Google Sheet."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not creds_dict:
            return False, "No GCP service account found in secrets.toml"
        creds = Credentials.from_service_account_info(
            dict(creds_dict),
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(url)
        ws = sh.sheet1
        ws.clear()
        ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())
        return True, "✅ Synced to Google Sheets!"
    except Exception as e:
        return False, f"❌ {e}"


def _append_to_sheets(row_data: dict, url: str):
    """Append a single row to Google Sheet."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = st.secrets.get("gcp_service_account", {})
        if not creds_dict:
            return False, "No GCP service account found in secrets.toml"
        creds = Credentials.from_service_account_info(
            dict(creds_dict),
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_url(url)
        ws = sh.sheet1
        
        # Get all column headers
        headers = ws.row_values(1)
        
        # Create row values in correct order
        row_values = []
        for col in headers:
            row_values.append(row_data.get(col, ""))
        
        # Append row
        ws.append_row(row_values)
        return True, "✅ Row added to Google Sheets!"
    except Exception as e:
        return False, f"❌ {e}"


def _ensure_sample_transfers():
    """Create sample transfers.xlsx so the app works out of the box."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if os.path.exists(TRANSFERS_FILE):
        return
    
    rows = []
    agents = ["John Smith", "Sara Johnson", "Mike Wilson", "Emma Davis"]
    customers = ["Ahmed Hassan", "Mona Ibrahim", "Khaled Ali", "Nadia Samir", "Omar Farouk", 
                 "Layla Mahmoud", "Youssef Karim", "Hana Nasser", "Karim Adel", "Sara Tarek"]
    statuses = ["New", "Contacted", "Qualified", "Closed", "Lost"]
    campaigns = ["Campaign A", "Campaign B", "Campaign C"]
    providers = ["Provider A", "Provider B", "Provider C", "Provider D"]
    roof_types = ["Flat", "Pitched", "Tile", "Metal"]
    
    today = date.today()
    for i in range(50):
        d = today - timedelta(days=random.randint(0, 60))
        agent = random.choice(agents)
        customer = random.choice(customers)
        rows.append({
            "Timestamp": d.strftime("%Y-%m-%d %H:%M:%S"),
            "Agent Name": agent,
            "Customer Name": customer,
            "Address": f"{random.randint(10, 999)} Main St, City {random.randint(1, 20)}",
            "Phone Number": f"01{random.randint(0, 9)}{random.randint(10000000, 99999999)}",
            "Electric Bill": f"{random.randint(50, 500)}",
            "Utility Provider": random.choice(providers),
            "Credit Score": random.randint(300, 850),
            "Email": f"{customer.lower().replace(' ', '.')}@email.com",
            "Transfer to": random.choice(["Company A", "Company B", "Company C"]),
            "Campaign": random.choice(campaigns),
            "Customer Name 2": customer,
            "Customer phone number": f"01{random.randint(0, 9)}{random.randint(10000000, 99999999)}",
            "Address 2": f"{random.randint(10, 999)} Main St, City {random.randint(1, 20)}",
            "Email 2": f"{customer.lower().replace(' ', '.')}@email.com",
            "Roof Type": random.choice(roof_types),
            "Age of Roof": random.randint(1, 30),
            "Status": random.choice(statuses),
            "FeedBack": random.choice(["", "Good lead", "Not interested", "Follow up needed", "Call back requested"]),
            "H comments": random.choice(["", "Call back", "Send email", "Schedule meeting", ""]),
            "File": "",
        })
    
    df = pd.DataFrame(rows)
    df.to_excel(TRANSFERS_FILE, index=False)


def _load_transfers(agent_name: str, is_admin: bool):
    """
    Load transfers data — Google Sheets if URL is set, otherwise Excel.
    Returns (DataFrame, source_label).
    """
    _ensure_sample_transfers()
    
    sheet_url = get_transfers_sheet_url()

    if sheet_url:
        df = _fetch_sheet(sheet_url)
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
            if "Timestamp" in df.columns:
                df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
            if not is_admin and "Agent Name" in df.columns:
                df = df[df["Agent Name"] == agent_name]
            return df, "🟢 Google Sheets (live)"

    # Fallback → local Excel
    try:
        df = pd.read_excel(TRANSFERS_FILE)
        df.columns = [c.strip() for c in df.columns]
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        if not is_admin and "Agent Name" in df.columns:
            df = df[df["Agent Name"] == agent_name]
        return df, "🟡 Local Excel"
    except Exception as e:
        st.error(f"Error reading transfers data: {e}")
        return pd.DataFrame(), "❌ No data"


# ── Main render ───────────────────────────────────────────────────────────────

def render_transfers_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")
    agent_name = user.get("full_name", "")
    agent_id = user.get("employee_id", "")

    st.markdown("""
    <style>
    .kpi-card {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .kpi-number {
        font-size: 2rem;
        font-weight: 700;
        color: #E8EAF0;
    }
    .kpi-label {
        color: #8B90A8;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Google Sheets config panel (ADMIN ONLY) ──────────────────────────────
    if is_admin:
        with st.expander("🔗 Google Sheets Integration (Admin Only)", expanded=False):
            st.markdown("""
            <div style="background:rgba(79,107,255,0.08);border:1px solid rgba(79,107,255,0.2);
                        border-radius:10px;padding:0.75rem 1rem;font-size:0.83rem;color:#8B90A8;
                        margin-bottom:0.75rem;line-height:1.7">
                <strong style="color:#E8EAF0">How to connect:</strong><br>
                1. Open your Google Sheet → <b>File → Share → Anyone with link → Viewer</b><br>
                2. Paste the link below → click <b>Save</b><br>
                3. This will apply to <b>ALL</b> users.
            </div>
            """, unsafe_allow_html=True)

            current_url = get_transfers_sheet_url()

            col_url, col_save, col_refresh = st.columns([5, 1, 1])
            with col_url:
                sheet_url_input = st.text_input(
                    "Sheet URL",
                    value=current_url,
                    placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
                    label_visibility="collapsed",
                    key="transfers_sheet_input",
                )
            with col_save:
                if st.button("💾 Save for All", key="save_transfers_url", use_container_width=True):
                    set_transfers_sheet_url(sheet_url_input.strip())
                    _fetch_sheet.clear()
                    st.success("✅ Saved to database! Applied for ALL users.")
                    st.rerun()
            with col_refresh:
                if st.button("🔄 Refresh", key="refresh_transfers", use_container_width=True):
                    _fetch_sheet.clear()
                    st.rerun()

            if current_url:
                st.success(f"✅ Active URL: {current_url[:50]}...")
            else:
                st.info("ℹ️ No Google Sheet connected. Using local Excel file.")
    else:
        # Show status for non-admin users (read-only)
        current_url = get_transfers_sheet_url()
        if current_url:
            st.caption("🔗 Connected to Google Sheet (managed by Admin)")
        else:
            st.caption("📁 Using local Excel file")

    # ── Upload fallback (Admin only) ──────────────────────────────────────────
    if is_admin:
        with st.expander("📂 Upload transfers.xlsx (local fallback)", expanded=False):
            uploaded = st.file_uploader("Upload Excel", type=["xlsx", "xls"], key="transfers_upload")
            if uploaded:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(TRANSFERS_FILE, "wb") as f:
                    f.write(uploaded.read())
                st.success("transfers.xlsx updated!")
                st.rerun()
            st.markdown("""
            **Expected columns:** Timestamp, Agent Name, Customer Name, Address, Phone Number,
            Electric Bill, Utility Provider, Credit Score, Email, Transfer to, Campaign,
            Customer Name 2, Customer phone number, Address 2, Email 2, Roof Type, Age of Roof, Status, FeedBack, H comments, File
            """)

    # ── Add Transfer Form (ALL USERS) ──────────────────────────────────────────
    with st.expander("➕ Add New Transfer", expanded=False):
        st.markdown("""
        <div style="background:rgba(79,107,255,0.08);border:1px solid rgba(79,107,255,0.2);
                    border-radius:10px;padding:0.75rem 1rem;font-size:0.83rem;color:#8B90A8;
                    margin-bottom:0.75rem;">
            Fill in the details below to add a new transfer. 
            <span style="color:#4F6BFF;">Your name will be auto-filled as the Agent.</span>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("add_transfer_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                customer_name = st.text_input("Customer Name *", placeholder="Enter customer full name")
                address = st.text_input("Address *", placeholder="Enter customer address")
                phone = st.text_input("Phone Number *", placeholder="Enter phone number")
                email = st.text_input("Email", placeholder="Enter email address")
            
            with col2:
                utility_provider = st.text_input("Utility Provider *", placeholder="e.g., Provider A")
                electricity_bill = st.text_input("Electricity Bill *", placeholder="Enter bill amount")
                credit_score = st.text_input("Credit Score", placeholder="Enter credit score (300-850)")
                status = st.selectbox("Status", ["New", "Contacted", "Qualified", "Closed", "Lost"])
            
            # Hidden/auto fields
            st.caption(f"👤 Agent: {agent_name} (auto-assigned)")
            
            # Submit button
            submitted = st.form_submit_button("📤 Add Transfer", use_container_width=True, type="primary")
            
            if submitted:
                # Validate required fields
                if not customer_name or not address or not phone or not utility_provider or not electricity_bill:
                    st.error("❌ Please fill in all required fields (*).")
                else:
                    # Prepare row data
                    now = datetime.now()
                    row_data = {
                        "Timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                        "Agent Name": agent_name,
                        "Customer Name": customer_name,
                        "Address": address,
                        "Phone Number": phone,
                        "Electric Bill": electricity_bill,
                        "Utility Provider": utility_provider,
                        "Credit Score": credit_score if credit_score else "",
                        "Email": email if email else "",
                        "Transfer to": "",
                        "Campaign": "",
                        "Customer Name 2": "",
                        "Customer phone number": "",
                        "Address 2": "",
                        "Email 2": "",
                        "Roof Type": "",
                        "Age of Roof": "",
                        "Status": status,
                        "FeedBack": "",
                        "H comments": "",
                        "File": "",
                    }
                    
                    # Save to Google Sheet if URL is set
                    sheet_url = get_transfers_sheet_url()
                    if sheet_url:
                        success, msg = _append_to_sheets(row_data, sheet_url)
                        if success:
                            st.success(f"✅ Transfer added successfully to Google Sheets!")
                            st.balloons()
                            _fetch_sheet.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        # Save to local Excel
                        try:
                            df = pd.read_excel(TRANSFERS_FILE)
                            new_row = pd.DataFrame([row_data])
                            df = pd.concat([df, new_row], ignore_index=True)
                            df.to_excel(TRANSFERS_FILE, index=False)
                            st.success("✅ Transfer added successfully to local Excel!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error saving to local file: {e}")

    # ── Load data ─────────────────────────────────────────────────────────────
    df, source = _load_transfers(agent_name, is_admin)

    col_src, col_ts = st.columns([3, 1])
    with col_src:
        st.caption(f"Data source: **{source}**")
    with col_ts:
        st.caption(f"As of: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    if df.empty:
        st.info("📭 No transfers data found. Upload transfers.xlsx or connect a Google Sheet.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    today = date.today()

    with col1:
        period = st.selectbox(
            "Period", ["All Time", "Today", "This Week", "This Month"], key="transfers_period"
        )
    with col2:
        statuses = ["All"] + sorted(df["Status"].dropna().unique().tolist()) if "Status" in df.columns else ["All"]
        status_filter = st.selectbox("Status", statuses, key="transfers_status")
    with col3:
        agents = ["All"] + sorted(df["Agent Name"].dropna().unique().tolist()) if "Agent Name" in df.columns else ["All"]
        agent_filter = st.selectbox("Agent", agents, key="transfers_agent")
    with col4:
        search = st.text_input("🔍 Search", placeholder="Customer, phone, address...", key="transfers_search")

    # Apply filters
    filtered = df.copy()
    if "Timestamp" in filtered.columns:
        if period == "Today":
            filtered = filtered[filtered["Timestamp"].dt.date == today]
        elif period == "This Week":
            filtered = filtered[filtered["Timestamp"].dt.date >= today - timedelta(days=today.weekday())]
        elif period == "This Month":
            filtered = filtered[filtered["Timestamp"].dt.date >= today.replace(day=1)]

    if status_filter != "All" and "Status" in filtered.columns:
        filtered = filtered[filtered["Status"] == status_filter]
    if agent_filter != "All" and "Agent Name" in filtered.columns:
        filtered = filtered[filtered["Agent Name"] == agent_filter]
    if search:
        mask = pd.Series(False, index=filtered.index)
        search_cols = ["Customer Name", "Phone Number", "Address", "Email", "Agent Name"]
        for col in search_cols:
            if col in filtered.columns:
                mask |= filtered[col].astype(str).str.contains(search, case=False, na=False)
        filtered = filtered[mask]

    # ── KPI cards ─────────────────────────────────────────────────────────────
    total_transfers = len(filtered)
    total_agents = filtered["Agent Name"].nunique() if "Agent Name" in filtered.columns else 0
    
    closed_count = 0
    if "Status" in filtered.columns:
        closed_count = sum(1 for s in filtered["Status"] if str(s).strip().lower() == "closed")
    
    new_count = 0
    if "Status" in filtered.columns:
        new_count = sum(1 for s in filtered["Status"] if str(s).strip().lower() == "new")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📊 Total Transfers", total_transfers)
    with col2:
        st.metric("👤 Agents", total_agents)
    with col3:
        st.metric("📌 New", new_count)
    with col4:
        st.metric("✅ Closed", closed_count)
    with col5:
        rate = round((closed_count / total_transfers) * 100, 1) if total_transfers > 0 else 0
        st.metric("🎯 Close Rate", f"{rate}%")

    # ── Charts ─────────────────────────────────────────────────────────────────
    try:
        import plotly.express as px

        if "Timestamp" in filtered.columns and not filtered.empty:

            col_l, col_r = st.columns(2)

            with col_l:
                daily = (
                    filtered.groupby(filtered["Timestamp"].dt.date)
                    .size()
                    .reset_index(name="count")
                )
                daily.columns = ["Date", "Count"]
                daily = daily.sort_values("Date")
                fig = px.bar(
                    daily, x="Date", y="Count",
                    title="📈 Transfers Trend",
                    template="plotly_dark",
                    color_discrete_sequence=["#4F6BFF"],
                )
                fig.update_layout(
                    paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                    font_color="#C8CADE",
                    margin=dict(l=10, r=10, t=45, b=10),
                    title_font_size=13,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col_r:
                if "Status" in filtered.columns:
                    sc = filtered["Status"].value_counts().reset_index()
                    sc.columns = ["Status", "Count"]
                    fig2 = px.pie(
                        sc, values="Count", names="Status",
                        title="🥧 Transfers by Status",
                        template="plotly_dark",
                        color_discrete_sequence=["#4F6BFF", "#7C3AED", "#06D6A0", "#FF6B6B", "#FFD166"],
                    )
                    fig2.update_layout(
                        paper_bgcolor="#1A1D27", font_color="#C8CADE",
                        margin=dict(l=10, r=10, t=45, b=10),
                        title_font_size=13,
                    )
                    st.plotly_chart(fig2, use_container_width=True)

            col_l2, col_r2 = st.columns(2)

            with col_l2:
                if "Agent Name" in filtered.columns:
                    by_agent = (
                        filtered.groupby("Agent Name")
                        .size()
                        .reset_index(name="count")
                        .sort_values("count", ascending=False)
                        .head(10)
                    )
                    fig3 = px.bar(
                        by_agent, x="count", y="Agent Name",
                        orientation="h",
                        title="👤 Transfers by Agent",
                        template="plotly_dark",
                        color_discrete_sequence=["#7C3AED"],
                    )
                    fig3.update_layout(
                        paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                        font_color="#C8CADE",
                        margin=dict(l=10, r=10, t=45, b=10),
                        title_font_size=13,
                        yaxis=dict(autorange="reversed"),
                    )
                    st.plotly_chart(fig3, use_container_width=True)

            with col_r2:
                if "Utility Provider" in filtered.columns:
                    by_provider = (
                        filtered.groupby("Utility Provider")
                        .size()
                        .reset_index(name="count")
                        .sort_values("count", ascending=False)
                        .head(10)
                    )
                    fig4 = px.pie(
                        by_provider, values="count", names="Utility Provider",
                        title="⚡ Utility Provider Distribution",
                        template="plotly_dark",
                        color_discrete_sequence=["#06D6A0", "#4F6BFF", "#7C3AED", "#FF9F43"],
                    )
                    fig4.update_layout(
                        paper_bgcolor="#1A1D27", font_color="#C8CADE",
                        margin=dict(l=10, r=10, t=45, b=10),
                        title_font_size=13,
                    )
                    st.plotly_chart(fig4, use_container_width=True)

    except ImportError:
        st.info("Install plotly for charts: `pip install plotly`")

    # ── Table ─────────────────────────────────────────────────────────────────
    st.markdown("#### 📋 Transfers Records")
    
    show_cols = ["Timestamp", "Agent Name", "Customer Name", "Phone Number", "Address", 
                 "Electric Bill", "Utility Provider", "Status"]
    available_cols = [c for c in show_cols if c in filtered.columns]
    
    if available_cols:
        st.dataframe(filtered[available_cols].reset_index(drop=True), use_container_width=True, height=340)
    else:
        st.dataframe(filtered.reset_index(drop=True), use_container_width=True, height=340)

    # ── Export (admin only) ───────────────────────────────────────────────────
    if is_admin:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Export to CSV",
                filtered.to_csv(index=False).encode(),
                "transfers_export.csv",
                "text/csv",
                use_container_width=True,
            )
        with c2:
            sheet_url_write = get_transfers_sheet_url()
            if sheet_url_write:
                if st.button("📤 Push to Google Sheets", key="push_transfers", use_container_width=True):
                    ok, msg = _push_to_sheets(filtered, sheet_url_write)
                    st.success(msg) if ok else st.error(msg)
            else:
                st.button("📤 Push to Google Sheets", disabled=True,
                          help="Save a Sheet URL first", use_container_width=True,
                          key="push_transfers_disabled")
