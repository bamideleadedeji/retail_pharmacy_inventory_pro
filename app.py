"""
International Hybrid Retail, Pharmacy & Restaurant Inventory, FEFO Expiry & Shrinkage Suite (v2.0)
Interactive Multi-Segment Operations Dashboard + 3-Sheet Excel Audit Workbook Export
"""

import io
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import plotly.express as px
from inventory_engine import DEFAULT_INVENTORY, audit_hybrid_inventory

st.set_page_config(page_title="Hybrid Retail, Pharmacy & Restaurant Inventory Suite", page_icon="🏪", layout="wide")
st.title("🏪 International Hybrid Retail, Pharmacy & Restaurant Inventory Suite")
st.caption("FEFO Pharmacy Batch Expiry Control • Restaurant Food-Cost & Shrinkage Audit • Retail Automated Reorder Points • Excel Workbook Export")
st.divider()

segment_filter = st.sidebar.multiselect("Filter Business Segment", ["Retail", "Pharmacy", "Restaurant"], default=["Retail", "Pharmacy", "Restaurant"])
uploaded = st.sidebar.file_uploader("Upload Custom Stock Count Sheet (.csv or .xlsx)", type=["csv", "xlsx"])
base_df = (pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)) if uploaded else pd.DataFrame(DEFAULT_INVENTORY)
if segment_filter:
    base_df = base_df[base_df["Segment"].isin(segment_filter)].reset_index(drop=True)

st.subheader("Interactive Physical vs. System Stock Count & Batch Expiry Ledger")
st.caption("Edit any stock count, daily usage, or expiry date below to recalculate FEFO alerts, shrinkage variance, and reorder points.")
edited_df = st.data_editor(base_df, width="stretch", num_rows="dynamic")

res = audit_hybrid_inventory(edited_df)
out_df = res["df"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Stock Valuation", f"${res['total_value']:,.2f}", delta=f"Avg Gross Margin: {res['avg_margin_pct']:.1f}%")
c2.metric("Physical Shrinkage Variance", f"${res['total_shrinkage']:,.2f}", delta="Theft / Spoilage Audit")
c3.metric("SKUs Below Reorder Point", f"{res['reorder_count']}", delta="Purchase Orders Needed")
c4.metric("FEFO Expiry Watch Items", f"{res['expiry_alerts']}", delta="Pharmacy & Perishables")

tab1, tab2, tab3 = st.tabs(["📊 Full Audit & FEFO Matrix", "📈 Valuation & Margin Analytics", "📥 3-Sheet Excel Workbook Export"])

with tab1:
    st.dataframe(out_df, width="stretch")

with tab2:
    col_a, col_b = st.columns(2)
    col_a.plotly_chart(px.bar(out_df, x="Item_Name", y="Inventory_Value_USD", color="Segment", title="Stock Valuation by SKU & Segment ($ USD)"), width="stretch")
    col_b.plotly_chart(px.bar(out_df, x="Item_Name", y="Days_Of_Cover", color="Replenishment_Action", title="Days of Inventory Cover vs. Reorder Status"), width="stretch")

with tab3:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame([
            {"Audit_Metric": "Report Generated (UTC)", "Value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")},
            {"Audit_Metric": "Total Physical Inventory Value ($)", "Value": f"${res['total_value']:,.2f}"},
            {"Audit_Metric": "Net Shrinkage / Spoilage Variance ($)", "Value": f"${res['total_shrinkage']:,.2f}"},
            {"Audit_Metric": "SKUs Requiring Immediate Reorder", "Value": res["reorder_count"]},
            {"Audit_Metric": "FEFO Batch Expiry Alerts", "Value": res["expiry_alerts"]},
            {"Audit_Metric": "Average Gross Margin (%)", "Value": f"{res['avg_margin_pct']:.1f}%"},
        ]).to_excel(writer, sheet_name="01_Executive_Stock_Summary", index=False)
        out_df.to_excel(writer, sheet_name="02_Master_Inventory_Audit", index=False)
        out_df[out_df["Replenishment_Action"] == "REORDER NOW"].to_excel(writer, sheet_name="03_Purchase_Order_Queue", index=False)

    st.download_button("📊 Download 3-Sheet Hybrid Inventory & FEFO Excel Workbook (.xlsx)", buf.getvalue(), "Hybrid_Retail_Pharmacy_Restaurant_Inventory_Suite.xlsx")
