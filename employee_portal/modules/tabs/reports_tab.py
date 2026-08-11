"""
modules/tabs/reports_tab.py
PDF Reports for employees — attendance, breaks, callbacks, and sales.
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
from io import BytesIO
from fpdf import FPDF

from modules.database import (
    get_attendance, get_breaks, get_callbacks, get_all_users, get_employee
)

# ── Try to import sales data ──────────────────────────────────────────────────
try:
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    SALES_FILE = os.path.join(DATA_DIR, "sales.xlsx")
    if os.path.exists(SALES_FILE):
        sales_df = pd.read_excel(SALES_FILE)
    else:
        sales_df = pd.DataFrame()
except:
    sales_df = pd.DataFrame()


class PDFReport(FPDF):
    """Custom PDF class for employee reports with UTF-8 support."""
    
    def __init__(self, employee, stats):
        super().__init__()
        self.employee = employee
        self.stats = stats
        self.set_auto_page_break(auto=True, margin=15)
        
        # Add Unicode font (DejaVu)
        try:
            # Try to use built-in DejaVu font
            self.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
            self.add_font('DejaVu', 'B', 'DejaVuSansCondensed-Bold.ttf', uni=True)
            self.font_name = 'DejaVu'
        except:
            # Fallback to Helvetica (ASCII only)
            self.font_name = 'Helvetica'
    
    def header(self):
        """Header for each page."""
        self.set_fill_color(26, 29, 39)
        self.rect(0, 0, 210, 30, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_name, 'B', 16)
        self.cell(0, 10, 'Employee Performance Report', 0, 1, 'C')
        
        self.set_font(self.font_name, '', 10)
        self.set_text_color(180, 180, 180)
        self.cell(0, 6, f'Generated: {datetime.now().strftime("%B %d, %Y %I:%M %p")}', 0, 1, 'C')
        
        self.ln(5)
    
    def footer(self):
        """Footer for each page."""
        self.set_y(-15)
        self.set_text_color(128, 128, 128)
        self.set_font(self.font_name, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        """Section title."""
        self.set_fill_color(26, 29, 39)
        self.rect(10, self.get_y(), 190, 8, 'F')
        
        self.set_text_color(232, 234, 240)
        self.set_font(self.font_name, 'B', 12)
        # Remove emojis for PDF compatibility
        clean_title = ''.join(c for c in title if ord(c) < 0x10000)
        self.cell(0, 8, f'  {clean_title}', 0, 1, 'L')
        self.ln(2)
    
    def add_stats_row(self, label, value):
        """Add a statistics row."""
        self.set_font(self.font_name, '', 10)
        self.set_text_color(139, 144, 168)
        # Remove emojis for PDF compatibility
        clean_label = ''.join(c for c in label if ord(c) < 0x10000)
        self.cell(80, 7, clean_label, 0, 0, 'L')
        self.set_text_color(200, 202, 222)
        self.cell(0, 7, str(value), 0, 1, 'L')
    
    def add_divider(self):
        """Add a horizontal divider."""
        self.set_draw_color(46, 51, 80)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)


def generate_employee_report(employee_id: str) -> BytesIO:
    """
    Generate a PDF report for a specific employee.
    Returns BytesIO object.
    """
    # ── Get employee data ─────────────────────────────────────────────────────
    employee = get_employee(employee_id)
    if not employee:
        return None
    
    # ── Get statistics ───────────────────────────────────────────────────────
    attendance = get_attendance(employee_id)
    breaks_data = get_breaks(employee_id)
    callbacks = get_callbacks(employee_id)
    
    # Sales data for this employee
    emp_sales = pd.DataFrame()
    if not sales_df.empty and "Employee_ID" in sales_df.columns:
        emp_sales = sales_df[sales_df["Employee_ID"] == employee_id]
    
    # ── Calculate stats ──────────────────────────────────────────────────────
    total_days = len(attendance)
    present = sum(1 for a in attendance if a["status"] == "Present")
    late = sum(1 for a in attendance if a["status"] == "Late")
    absent = total_days - present - late
    att_rate = round(present / total_days * 100) if total_days else 0
    
    completed_breaks = [b for b in breaks_data if b.get("duration")]
    total_break_min = sum(b["duration"] for b in completed_breaks)
    total_breaks = len(completed_breaks)
    avg_break = round(total_break_min / total_breaks, 1) if total_breaks else 0
    
    total_cb = len(callbacks)
    completed_cb = sum(1 for c in callbacks if c["status"] == "Completed")
    pending_cb = sum(1 for c in callbacks if c["status"] in ["Pending", "Cold", "Warm", "Hot"])
    cb_rate = round(completed_cb / total_cb * 100) if total_cb else 0
    
    # Sales stats
    total_revenue = 0
    total_sales = 0
    if not emp_sales.empty and "Revenue" in emp_sales.columns:
        total_revenue = emp_sales["Revenue"].sum()
        total_sales = len(emp_sales)
    
    stats = {
        "attendance": {
            "total_days": total_days,
            "present": present,
            "late": late,
            "absent": absent,
            "rate": att_rate,
        },
        "breaks": {
            "total": total_breaks,
            "total_minutes": total_break_min,
            "avg_minutes": avg_break,
        },
        "callbacks": {
            "total": total_cb,
            "completed": completed_cb,
            "pending": pending_cb,
            "rate": cb_rate,
        },
        "sales": {
            "total": total_sales,
            "revenue": total_revenue,
        }
    }
    
    # ── Create PDF ──────────────────────────────────────────────────────────
    pdf = PDFReport(employee, stats)
    pdf.add_page()
    
    # ── Employee Info ────────────────────────────────────────────────────────
    pdf.chapter_title("Employee Information")
    
    pdf.add_stats_row("Employee Name", employee.get("full_name", "—"))
    pdf.add_stats_row("Employee ID", employee.get("employee_id", "—"))
    pdf.add_stats_row("Department", employee.get("department", "—"))
    pdf.add_stats_row("Position", employee.get("position", "—"))
    pdf.add_stats_row("Email", employee.get("email", "—"))
    pdf.add_stats_row("Phone", employee.get("phone", "—"))
    pdf.add_stats_row("Hire Date", employee.get("hire_date", "—"))
    pdf.add_stats_row("Role", employee.get("role", "—").capitalize())
    
    pdf.ln(4)
    pdf.add_divider()
    
    # ── Attendance ──────────────────────────────────────────────────────────
    pdf.chapter_title("Attendance Summary")
    
    pdf.add_stats_row("Total Working Days", stats["attendance"]["total_days"])
    pdf.add_stats_row("Present", stats["attendance"]["present"])
    pdf.add_stats_row("Late", stats["attendance"]["late"])
    pdf.add_stats_row("Absent", stats["attendance"]["absent"])
    pdf.add_stats_row("Attendance Rate", f"{stats['attendance']['rate']}%")
    
    pdf.ln(4)
    pdf.add_divider()
    
    # ── Breaks ──────────────────────────────────────────────────────────────
    pdf.chapter_title("Break Summary")
    
    pdf.add_stats_row("Total Breaks Taken", stats["breaks"]["total"])
    pdf.add_stats_row("Total Break Time", f"{stats['breaks']['total_minutes']:.0f} min")
    pdf.add_stats_row("Average Break Duration", f"{stats['breaks']['avg_minutes']:.1f} min")
    
    pdf.ln(4)
    pdf.add_divider()
    
    # ── Callbacks ───────────────────────────────────────────────────────────
    pdf.chapter_title("Callback Summary")
    
    pdf.add_stats_row("Total Callbacks", stats["callbacks"]["total"])
    pdf.add_stats_row("Completed", stats["callbacks"]["completed"])
    pdf.add_stats_row("Pending", stats["callbacks"]["pending"])
    pdf.add_stats_row("Completion Rate", f"{stats['callbacks']['rate']}%")
    
    pdf.ln(4)
    pdf.add_divider()
    
    # ── Sales ──────────────────────────────────────────────────────────────
    pdf.chapter_title("Sales Summary")
    
    pdf.add_stats_row("Total Sales", stats["sales"]["total"])
    pdf.add_stats_row("Total Revenue", f"${stats['sales']['revenue']:,.2f}")
    
    pdf.ln(4)
    pdf.add_divider()
    
    # ── Recent Activity ─────────────────────────────────────────────────────
    pdf.chapter_title("Recent Activity")
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(139, 144, 168)
    
    # Get recent items
    recent_items = []
    
    # Add recent attendance (last 5)
    for a in attendance[:5]:
        recent_items.append({
            "date": a.get("date", ""),
            "type": "Check-in",
            "detail": f"{a.get('check_in', '')} ({a.get('status', '')})"
        })
    
    # Add recent breaks (last 5)
    for b in breaks_data[:5]:
        if b.get("duration"):
            recent_items.append({
                "date": b.get("date", ""),
                "type": "Break",
                "detail": f"{b.get('break_name', '')} - {b.get('duration', 0):.0f} min"
            })
    
    # Add recent callbacks (last 5)
    for c in callbacks[:5]:
        recent_items.append({
            "date": c.get("callback_date", ""),
            "type": "Callback",
            "detail": f"{c.get('customer_name', '')} - {c.get('status', '')}"
        })
    
    # Sort by date (newest first) and take top 8
    recent_items.sort(key=lambda x: x["date"], reverse=True)
    recent_items = recent_items[:8]
    
    if recent_items:
        for item in recent_items:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(200, 202, 222)
            pdf.cell(30, 6, item["date"], 0, 0, 'L')
            pdf.set_text_color(79, 107, 255)
            pdf.cell(30, 6, item["type"], 0, 0, 'L')
            pdf.set_text_color(200, 202, 222)
            pdf.cell(0, 6, item["detail"], 0, 1, 'L')
    else:
        pdf.add_stats_row("No recent activity", "")
    
    # ── Output ──────────────────────────────────────────────────────────────
    pdf_bytes = pdf.output(dest='S')
    
    return BytesIO(pdf_bytes)


def render_reports_tab(user: dict):
    """Render the reports tab in Streamlit."""
    is_admin = user["role"] in ("admin", "leader")
    
    st.markdown("""
    <style>
    .report-card {
        background: #1A1D27;
        border: 1px solid #2E3350;
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .report-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #E8EAF0;
        margin-bottom: 0.5rem;
    }
    .report-sub {
        color: #8B90A8;
        font-size: 0.85rem;
        margin-bottom: 0.75rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="report-card">
        <div class="report-title">📊 Generate Performance Report</div>
        <div class="report-sub">
            Generate a detailed PDF report for any employee including attendance, breaks, callbacks, and sales.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ── Employee Selection ──────────────────────────────────────────────────
    if is_admin:
        employees = get_all_users()
        emp_options = {
            f"{e.get('full_name', '')} ({e.get('employee_id', '')})": e.get("employee_id")
            for e in employees
        }
        selected_label = st.selectbox("Select Employee", list(emp_options.keys()), key="report_emp_select")
        selected_emp_id = emp_options[selected_label]
    else:
        selected_emp_id = user.get("employee_id")
        st.info(f"👤 Generating report for: **{user.get('full_name', '')}**")
    
    # ── Generate Button ─────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("📄 Generate PDF Report", use_container_width=True, type="primary"):
            with st.spinner("Generating report..."):
                pdf_bytes = generate_employee_report(selected_emp_id)
                if pdf_bytes:
                    employee = get_employee(selected_emp_id)
                    filename = f"report_{employee.get('full_name', 'employee').replace(' ', '_')}_{date.today()}.pdf"
                    
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_report"
                    )
                    st.success("✅ Report generated successfully!")
                else:
                    st.error("❌ Failed to generate report. Please try again.")
    
    # ── Preview Stats ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Report Preview")
    
    # Show quick stats for selected employee
    emp = get_employee(selected_emp_id)
    if emp:
        attendance = get_attendance(selected_emp_id)
        breaks_data = get_breaks(selected_emp_id)
        callbacks = get_callbacks(selected_emp_id)
        
        total_days = len(attendance)
        present = sum(1 for a in attendance if a["status"] == "Present")
        att_rate = round(present / total_days * 100) if total_days else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("👤 Employee", emp.get("full_name", "—"))
        with col2:
            st.metric("📊 Attendance Rate", f"{att_rate}%")
        with col3:
            st.metric("📞 Total Callbacks", len(callbacks))
        with col4:
            total_breaks = len([b for b in breaks_data if b.get("duration")])
            st.metric("☕ Total Breaks", total_breaks)
