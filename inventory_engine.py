"""
International Hybrid Retail, Pharmacy & Restaurant Inventory, FEFO Expiry & Shrinkage Audit Engine
Computes EOQ reorder points, days-of-cover, FEFO pharmacy expiry risk, restaurant COGS %, and shrinkage variance.
"""

import math
from datetime import datetime, timedelta
import pandas as pd

today = datetime.now().date()

DEFAULT_INVENTORY = [
    {"SKU": "PHM-101", "Item_Name": "Amoxicillin 500mg Caps (Box/100)", "Segment": "Pharmacy", "Batch_No": "B26-881", "Expiry_Date": str(today + timedelta(days=22)), "Physical_Units": 48, "System_Units": 50, "Daily_Usage": 3.5, "Lead_Time_Days": 5, "Unit_Cost_USD": 8.40, "Selling_Price_USD": 16.50},
    {"SKU": "PHM-102", "Item_Name": "Insulin Glargine Pen (5-Pack)", "Segment": "Pharmacy", "Batch_No": "B26-412", "Expiry_Date": str(today + timedelta(days=75)), "Physical_Units": 18, "System_Units": 18, "Daily_Usage": 1.8, "Lead_Time_Days": 7, "Unit_Cost_USD": 42.00, "Selling_Price_USD": 68.00},
    {"SKU": "RST-201", "Item_Name": "Prime Ribeye Beef Cuts (kg)", "Segment": "Restaurant", "Batch_No": "R26-09", "Expiry_Date": str(today + timedelta(days=6)), "Physical_Units": 34, "System_Units": 39, "Daily_Usage": 8.0, "Lead_Time_Days": 2, "Unit_Cost_USD": 18.50, "Selling_Price_USD": 44.00},
    {"SKU": "RST-202", "Item_Name": "Extra Virgin Olive Oil (5L Tin)", "Segment": "Restaurant", "Batch_No": "R26-14", "Expiry_Date": str(today + timedelta(days=240)), "Physical_Units": 22, "System_Units": 23, "Daily_Usage": 1.5, "Lead_Time_Days": 4, "Unit_Cost_USD": 31.00, "Selling_Price_USD": 78.00},
    {"SKU": "RTL-301", "Item_Name": "Organic Arabica Whole Bean (1kg)", "Segment": "Retail", "Batch_No": "M26-55", "Expiry_Date": str(today + timedelta(days=150)), "Physical_Units": 95, "System_Units": 96, "Daily_Usage": 6.2, "Lead_Time_Days": 6, "Unit_Cost_USD": 11.20, "Selling_Price_USD": 22.99},
    {"SKU": "RTL-302", "Item_Name": "Vitamin D3 5000IU Softgels", "Segment": "Retail", "Batch_No": "M26-61", "Expiry_Date": str(today + timedelta(days=190)), "Physical_Units": 14, "System_Units": 15, "Daily_Usage": 4.0, "Lead_Time_Days": 5, "Unit_Cost_USD": 6.50, "Selling_Price_USD": 14.99},
]


def audit_hybrid_inventory(df: pd.DataFrame) -> dict:
    work = df.copy()
    now_d = datetime.now().date()

    days_to_exp, exp_status, shrink_units, shrink_val = [], [], [], []
    days_cover, reorder_pt, stock_status, gross_margin_pct, stock_val = [], [], [], [], []

    for _, row in work.iterrows():
        phys = float(row.get("Physical_Units", 0.0))
        sys_u = float(row.get("System_Units", phys))
        usage = max(float(row.get("Daily_Usage", 0.1)), 0.05)
        lead = float(row.get("Lead_Time_Days", 3.0))
        cost = float(row.get("Unit_Cost_USD", 0.0))
        price = max(float(row.get("Selling_Price_USD", cost)), 0.01)

        # 1. FEFO Expiry Audit
        try:
            exp_dt = datetime.strptime(str(row.get("Expiry_Date", ""))[:10], "%Y-%m-%d").date()
            d_exp = (exp_dt - now_d).days
        except Exception:
            d_exp = 365
        days_to_exp.append(d_exp)
        if d_exp <= 14:
            exp_status.append("URGENT FEFO MARKDOWN (<=14d)")
        elif d_exp <= 45:
            exp_status.append("WATCH EXPIRY (15-45d)")
        else:
            exp_status.append("SAFE SHELF LIFE")

        # 2. Shrinkage & Reconciliation Variance
        s_u = round(phys - sys_u, 2)
        s_v = round(s_u * cost, 2)
        shrink_units.append(s_u)
        shrink_val.append(s_v)

        # 3. Reorder Point & Days of Cover
        safety_stock = math.ceil(usage * 2.0)
        rop = math.ceil(usage * lead + safety_stock)
        d_cov = round(phys / usage, 1)
        reorder_pt.append(rop)
        days_cover.append(d_cov)
        stock_status.append("REORDER NOW" if phys <= rop else "OPTIMAL STOCK")

        # 4. Valuation & Margin
        stock_val.append(round(phys * cost, 2))
        gross_margin_pct.append(round((price - cost) / price * 100.0, 1))

    work["Days_To_Expiry"] = days_to_exp
    work["FEFO_Alert"] = exp_status
    work["Shrinkage_Units"] = shrink_units
    work["Shrinkage_Value_USD"] = shrink_val
    work["Days_Of_Cover"] = days_cover
    work["Reorder_Point"] = reorder_pt
    work["Replenishment_Action"] = stock_status
    work["Inventory_Value_USD"] = stock_val
    work["Gross_Margin_Pct"] = gross_margin_pct

    return {
        "df": work,
        "total_value": round(float(work["Inventory_Value_USD"].sum()), 2),
        "total_shrinkage": round(float(work["Shrinkage_Value_USD"].sum()), 2),
        "reorder_count": int((work["Replenishment_Action"] == "REORDER NOW").sum()),
        "expiry_alerts": int((work["FEFO_Alert"] != "SAFE SHELF LIFE").sum()),
        "avg_margin_pct": round(float(work["Gross_Margin_Pct"].mean()), 1),
    }
