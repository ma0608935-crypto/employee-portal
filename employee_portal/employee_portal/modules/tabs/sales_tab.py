"""
modules/tabs/sales_tab.py
Sales tab — Google Sheets as primary live source with auto-refresh,
Excel fallback, all charts update from whatever source is active.
"""

import streamlit as st
import pandas as pd
import os
from datetime import date, timedelta

DATA_DIR   = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
SALES_FILE = os.path.join(DATA_DIR, "sales.xlsx")

LOGO = "https://plain-eeur-prod-public.komododecks.com/202608/09/cTbwjWfVAMvKzMZ4n8ET/image.png"


# ── Google Sheets helpers ─────────────────────────────────────────────────────

@st.cache_data(ttl=60)   # cache for 60 s so charts don't re-fetch on every widget touch
def _fetch_sheet(sheet_url: str) -> pd.DataFrame:
    """Download a public Google Sheet as CSV and return a DataFrame."""
    try:
        if "/d/" in sheet_url:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
            # try to get gid (tab id) if present
            gid = "0"
            if "gid=" in sheet_url:
                gid = sheet_url.split("gid=")[1].split("&")[0].split("#")[0]
            csv_url = (
                f"https://docs.google.com/spreadsheets/d/{sheet_id}"
                f"/export?format=csv&gid={gid}"
            )
        else:
            csv_url = sheet_url   # already a direct CSV URL
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        return pd.DataFrame()


def _push_to_sheets(df: pd.DataFrame, url: str):
    """Write DataFrame back to a Google Sheet (needs service account in secrets)."""
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
        gc  = gspread.authorize(creds)
        sh  = gc.open_by_url(url)
        ws  = sh.sheet1
        ws.clear()
        ws.update([df.columns.tolist()] + df.fillna("").astype(str).values.tolist())
        return True, "✅ Synced to Google Sheets!"
    except Exception as e:
        return False, f"❌ {e}"


def _ensure_sample_sales():
    """Create sample sales.xlsx so the app works out of the box."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SALES_FILE):
        import random
        rows = []
        products = ["Product A", "Product B", "Product C", "Service X", "Service Y"]
        emp_ids  = ["EMP-001", "EMP-002"]
        statuses = ["Completed", "Pending", "Cancelled"]
        today = date.today()
        for i in range(90):
            d = today - timedelta(days=i)
            for emp in emp_ids:
                if random.random() > 0.3:
                    rows.append({
                        "Date":        d.strftime("%Y-%m-%d"),
                        "Employee_ID": emp,
                        "Product":     random.choice(products),
                        "Amount":      random.randint(1, 20),
                        "Revenue":     round(random.uniform(500, 5000), 2),
                        "Status":      random.choice(statuses),
                    })
        pd.DataFrame(rows).to_excel(SALES_FILE, index=False)


def _load_sales(employee_id: str, is_admin: bool):
    """
    Load sales data — Google Sheets if URL is set, otherwise Excel.
    Returns (DataFrame, source_label).
    """
    sheet_url = st.session_state.get("sales_sheet_url", "").strip()

    if sheet_url:
        df = _fetch_sheet(sheet_url)
        if not df.empty:
            df.columns = [c.strip() for c in df.columns]
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            if not is_admin and "Employee_ID" in df.columns:
                df = df[df["Employee_ID"] == employee_id]
            return df, "🟢 Google Sheets (live)"

    # Fallback → local Excel
    _ensure_sample_sales()
    try:
        df = pd.read_excel(SALES_FILE)
        df.columns = [c.strip() for c in df.columns]
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        if not is_admin and "Employee_ID" in df.columns:
            df = df[df["Employee_ID"] == employee_id]
        return df, "🟡 Local Excel (upload or connect a Sheet)"
    except Exception as e:
        st.error(f"Error reading sales data: {e}")
        return pd.DataFrame(), "❌ No data"


# ── Main render ───────────────────────────────────────────────────────────────

def render_sales_tab(user: dict):
    is_admin = user["role"] in ("admin", "leader")

    # ── Google Sheets config panel ────────────────────────────────────────────
    with st.expander("🔗 Google Sheets Integration", expanded=False):
        st.markdown("""
        <div style="background:rgba(79,107,255,0.08);border:1px solid rgba(79,107,255,0.2);
                    border-radius:10px;padding:0.75rem 1rem;font-size:0.83rem;color:#8B90A8;
                    margin-bottom:0.75rem;line-height:1.7">
            <strong style="color:#E8EAF0">How to connect:</strong><br>
            1. Open your Google Sheet → <b>File → Share → Anyone with link → Viewer</b><br>
            2. Paste the link below → click <b>Save & Sync</b><br>
            3. Charts and table update automatically every 60 seconds.<br>
            <span style="color:#4F6BFF">To also <b>push</b> data back, add a service account to secrets.toml.</span>
        </div>
        """, unsafe_allow_html=True)

        col_url, col_save, col_refresh = st.columns([5, 1, 1])
        with col_url:
            sheet_url_input = st.text_input(
                "Sheet URL",
                value=st.session_state.get("sales_sheet_url", ""),
                placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit",
                label_visibility="collapsed",
                key="sales_sheet_input",
            )
        with col_save:
            if st.button("💾 Save", key="save_sales_url", use_container_width=True):
                st.session_state.sales_sheet_url = sheet_url_input.strip()
                _fetch_sheet.clear()          # bust cache so next load is fresh
                st.success("Saved!")
                st.rerun()
        with col_refresh:
            if st.button("🔄 Refresh", key="refresh_sales", use_container_width=True):
                _fetch_sheet.clear()
                st.rerun()

    # ── Upload fallback ───────────────────────────────────────────────────────
    with st.expander("📂 Upload sales.xlsx (local fallback)", expanded=False):
        uploaded = st.file_uploader("Upload Excel", type=["xlsx", "xls"], key="sales_upload")
        if uploaded:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(SALES_FILE, "wb") as f:
                f.write(uploaded.read())
            st.success("sales.xlsx updated!")
            st.rerun()
        st.markdown("""
        **Expected columns:** `Date` · `Employee_ID` · `Product` · `Amount` · `Revenue` · `Status`
        """)

    # ── Load data ─────────────────────────────────────────────────────────────
    df, source = _load_sales(user.get("employee_id", ""), is_admin)

    col_src, col_ts = st.columns([3, 1])
    with col_src:
        st.caption(f"Data source: **{source}**")
    with col_ts:
        st.caption(f"As of: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    if df.empty:
        st.info("No sales data found. Connect a Google Sheet or upload sales.xlsx.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    today = date.today()

    with col1:
        period = st.selectbox(
            "Period", ["All Time", "Today", "This Week", "This Month"], key="sales_period"
        )
    with col2:
        products = ["All"] + sorted(df["Product"].dropna().unique().tolist()) \
            if "Product" in df.columns else ["All"]
        prod_filter = st.selectbox("Product", products, key="sales_prod")
    with col3:
        statuses = ["All"] + sorted(df["Status"].dropna().unique().tolist()) \
            if "Status" in df.columns else ["All"]
        stat_filter = st.selectbox("Status", statuses, key="sales_stat")
    with col4:
        search = st.text_input("🔍 Search", placeholder="Product or Employee…",
                               key="sales_search")

    # Apply filters
    filtered = df.copy()
    if "Date" in filtered.columns:
        if period == "Today":
            filtered = filtered[filtered["Date"].dt.date == today]
        elif period == "This Week":
            filtered = filtered[
                filtered["Date"].dt.date >= today - timedelta(days=today.weekday())]
        elif period == "This Month":
            filtered = filtered[filtered["Date"].dt.date >= today.replace(day=1)]

    if prod_filter != "All" and "Product" in filtered.columns:
        filtered = filtered[filtered["Product"] == prod_filter]
    if stat_filter != "All" and "Status" in filtered.columns:
        filtered = filtered[filtered["Status"] == stat_filter]
    if search:
        mask = pd.Series(False, index=filtered.index)
        for col in ["Product", "Employee_ID", "Status"]:
            if col in filtered.columns:
                mask |= filtered[col].astype(str).str.contains(search, case=False, na=False)
        filtered = filtered[mask]

    # ── KPI cards ─────────────────────────────────────────────────────────────
    rev_col = "Revenue" if "Revenue" in filtered.columns else None
    amt_col = "Amount"  if "Amount"  in filtered.columns else None

    total_rev  = filtered[rev_col].sum()          if rev_col and not filtered.empty else 0
    total_sales = len(filtered)
    completed  = len(filtered[filtered["Status"] == "Completed"]) \
        if "Status" in filtered.columns else 0
    avg_rev    = filtered[rev_col].mean()          if rev_col and not filtered.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Revenue",  f"${total_rev:,.2f}")
    with c2: st.metric("Total Sales",    total_sales)
    with c3: st.metric("Completed",      completed)
    with c4: st.metric("Avg Revenue",    f"${avg_rev:,.2f}")

    # ── Charts (all built from `filtered` so they react to sheet + filters) ───
    try:
        import plotly.express as px

        if "Date" in filtered.columns and rev_col and not filtered.empty:

            # Row 1: Line trend + Pie status
            col_l, col_r = st.columns(2)

            with col_l:
                daily = (
                    filtered.groupby(filtered["Date"].dt.date)[rev_col]
                    .sum()
                    .reset_index()
                )
                daily.columns = ["Date", "Revenue"]
                daily = daily.sort_values("Date")
                fig = px.line(
                    daily, x="Date", y="Revenue",
                    title="📈 Revenue Trend",
                    template="plotly_dark",
                    markers=True,
                    color_discrete_sequence=["#4F6BFF"],
                )
                fig.update_layout(
                    paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                    font_color="#C8CADE",
                    margin=dict(l=10, r=10, t=45, b=10),
                    title_font_size=13,
                )
                fig.update_traces(line_width=2.5)
                st.plotly_chart(fig, use_container_width=True)

            with col_r:
                if "Status" in filtered.columns:
                    sc = filtered["Status"].value_counts().reset_index()
                    sc.columns = ["Status", "Count"]
                    fig2 = px.pie(
                        sc, values="Count", names="Status",
                        title="🥧 Sales by Status",
                        template="plotly_dark",
                        color_discrete_sequence=["#4F6BFF", "#7C3AED", "#06D6A0", "#FF6B6B"],
                    )
                    fig2.update_layout(
                        paper_bgcolor="#1A1D27", font_color="#C8CADE",
                        margin=dict(l=10, r=10, t=45, b=10),
                        title_font_size=13,
                    )
                    st.plotly_chart(fig2, use_container_width=True)

            # Row 2: Monthly bar + Product bar (if enough data)
            col_l2, col_r2 = st.columns(2)

            with col_l2:
                monthly = (
                    filtered.groupby(filtered["Date"].dt.to_period("M"))[rev_col]
                    .sum()
                    .reset_index()
                )
                monthly["Date"] = monthly["Date"].astype(str)
                fig3 = px.bar(
                    monthly, x="Date", y=rev_col,
                    title="📅 Monthly Revenue",
                    template="plotly_dark",
                    color_discrete_sequence=["#7C3AED"],
                )
                fig3.update_layout(
                    paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                    font_color="#C8CADE",
                    margin=dict(l=10, r=10, t=45, b=10),
                    title_font_size=13,
                )
                st.plotly_chart(fig3, use_container_width=True)

            with col_r2:
                if "Product" in filtered.columns:
                    by_prod = (
                        filtered.groupby("Product")[rev_col]
                        .sum()
                        .reset_index()
                        .sort_values(rev_col, ascending=False)
                        .head(10)
                    )
                    fig4 = px.bar(
                        by_prod, x=rev_col, y="Product",
                        orientation="h",
                        title="🏆 Revenue by Product",
                        template="plotly_dark",
                        color_discrete_sequence=["#06D6A0"],
                    )
                    fig4.update_layout(
                        paper_bgcolor="#1A1D27", plot_bgcolor="#1A1D27",
                        font_color="#C8CADE",
                        margin=dict(l=10, r=10, t=45, b=10),
                        title_font_size=13,
                        yaxis=dict(autorange="reversed"),
                    )
                    st.plotly_chart(fig4, use_container_width=True)

        else:
            st.info("Not enough date/revenue data to draw charts.")

    except ImportError:
        st.info("Install plotly for charts: `pip install plotly`")

    # ── Table ─────────────────────────────────────────────────────────────────
    st.markdown("#### 📋 Sales Records")
    sort_options = filtered.columns.tolist()
    col_sort, col_asc = st.columns([3, 1])
    with col_sort:
        sort_col = st.selectbox("Sort by", sort_options, key="sales_sort")
    with col_asc:
        asc = st.checkbox("Ascending", value=False, key="sales_asc")

    if sort_col:
        filtered = filtered.sort_values(sort_col, ascending=asc)

    st.dataframe(filtered.reset_index(drop=True), use_container_width=True, height=340)

    # ── Export (admin only) ───────────────────────────────────────────────────
    if is_admin:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Export to CSV",
                filtered.to_csv(index=False).encode(),
                "sales_export.csv",
                "text/csv",
                use_container_width=True,
            )
        with c2:
            sheet_url_write = st.session_state.get("sales_sheet_url", "").strip()
            if sheet_url_write:
                if st.button("📤 Push to Google Sheets", key="push_sales",
                             use_container_width=True):
                    ok, msg = _push_to_sheets(filtered, sheet_url_write)
                    st.success(msg) if ok else st.error(msg)
            else:
                st.button("📤 Push to Google Sheets", disabled=True,
                          help="Save a Sheet URL first", use_container_width=True,
                          key="push_sales_disabled")
