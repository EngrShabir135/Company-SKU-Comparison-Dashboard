import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

st.title("📊 Company SKU Comparison Dashboard")

# =========================
# Upload File
# =========================
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file is not None:

    df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = df.columns.str.strip()

    # =========================
    # SKU STANDARDIZATION
    # =========================
    def map_sku(x):
        x = str(x).upper()

        if "SSRB" in x:
            return "SSRB"
        elif "350" in x:
            return "350ML"
        elif "500" in x:
            return "500ML"
        elif "1LTR" in x or "1 LTR" in x:
            return "1LTR"
        elif "2.25" in x:
            return "2.25LTR"
        elif "2LTR" in x:
            return "2LTR"
        elif "250" in x and "CAN" in x:
            return "250ML CAN"
        else:
            return None

    df["SKU_FINAL"] = df["SKUS"].apply(map_sku)

    sku_order = ["SSRB", "350ML", "500ML", "1LTR", "2LTR", "2.25LTR", "250ML CAN"]
    df = df[df["SKU_FINAL"].isin(sku_order)]

    # =========================
    # SIDEBAR FILTERS (FIXED KEYS)
    # =========================
    st.sidebar.header("Filters")

    company1 = st.sidebar.selectbox(
        "Select Company 1",
        sorted(df["COMPANY"].dropna().unique()),
        key="company1"
    )

    company2 = st.sidebar.selectbox(
        "Select Company 2",
        sorted(df["COMPANY"].dropna().unique()),
        key="company2"
    )

    metric = st.sidebar.selectbox(
        "Select Metric",
        ["SALE PRICE", "NTP", "ADJ SALE PRICE", "NTP/6P", "NET AMOUNT", "QUANTITY"],
        index=3,
        key="metric"
    )

    channel = st.sidebar.multiselect(
        "Select Channel",
        df["CHANNEL"].dropna().unique(),
        default=df["CHANNEL"].dropna().unique(),
        key="channel"
    )

    master_cat = st.sidebar.multiselect(
        "Master Category",
        df["MASTER CAT"].dropna().unique(),
        key="master_cat"
    )

    category = st.sidebar.multiselect(
        "Category",
        df["CATEGORY"].dropna().unique(),
        key="category"
    )

    period = st.sidebar.multiselect(
        "Select Period",
        df["PERIOD"].dropna().unique(),
        key="period"
    )

    brand1 = st.sidebar.multiselect(
        f"{company1} Brands",
        df[df["COMPANY"] == company1]["BRAND"].dropna().unique(),
        key="brand1"
    )

    brand2 = st.sidebar.multiselect(
        f"{company2} Brands",
        df[df["COMPANY"] == company2]["BRAND"].dropna().unique(),
        key="brand2"
    )

    # =========================
    # APPLY FILTERS
    # =========================
    filtered_df = df.copy()

    filtered_df = filtered_df[filtered_df["CHANNEL"].isin(channel)]

    if master_cat:
        filtered_df = filtered_df[filtered_df["MASTER CAT"].isin(master_cat)]

    if category:
        filtered_df = filtered_df[filtered_df["CATEGORY"].isin(category)]

    if period:
        filtered_df = filtered_df[filtered_df["PERIOD"].isin(period)]

    df1 = filtered_df[filtered_df["COMPANY"] == company1]
    df2 = filtered_df[filtered_df["COMPANY"] == company2]

    if brand1:
        df1 = df1[df1["BRAND"].isin(brand1)]

    if brand2:
        df2 = df2[df2["BRAND"].isin(brand2)]

    # =========================
    # AVG TABLE FUNCTION (PIVOT)
    # =========================
    def create_avg_table(df1, df2, metric):

        p1 = pd.pivot_table(
            df1,
            index="CITY",
            columns="SKU_FINAL",
            values=metric,
            aggfunc="mean"
        )

        p2 = pd.pivot_table(
            df2,
            index="CITY",
            columns="SKU_FINAL",
            values=metric,
            aggfunc="mean"
        )

        final = pd.DataFrame(index=sorted(set(p1.index).union(set(p2.index))))

        for sku in sku_order:
            c1_col = f"{company1}_{sku}"
            c2_col = f"{company2}_{sku}"
            idx_col = f"INDEX_{sku}"

            final[c1_col] = p1.get(sku)
            final[c2_col] = p2.get(sku)

            final[idx_col] = np.where(
                final[c2_col] == 0,
                np.nan,
                (final[c1_col] / final[c2_col]) * 100
            )

        return final.reset_index()

    # =========================
    # MIN MAX FUNCTION
    # =========================
    def create_min_max_table(df, metric):

        min_table = pd.pivot_table(
            df,
            index="CITY",
            columns="SKU_FINAL",
            values=metric,
            aggfunc="min"
        )

        max_table = pd.pivot_table(
            df,
            index="CITY",
            columns="SKU_FINAL",
            values=metric,
            aggfunc="max"
        )

        final = pd.DataFrame(index=min_table.index)

        for sku in sku_order:
            final[f"{sku}_MIN"] = min_table.get(sku)
            final[f"{sku}_MAX"] = max_table.get(sku)

        return final.reset_index()

    # =========================
    # CREATE TABLES
    # =========================
    avg_table = create_avg_table(df1, df2, metric)
    minmax_1 = create_min_max_table(df1, metric)
    minmax_2 = create_min_max_table(df2, metric)

    # =========================
    # DISPLAY
    # =========================
    st.subheader(f"📊 Average Comparison Table ({metric})")
    st.dataframe(avg_table, use_container_width=True)

    st.subheader(f"📉 {company1} Min / Max ({metric})")
    st.dataframe(minmax_1, use_container_width=True)

    st.subheader(f"📉 {company2} Min / Max ({metric})")
    st.dataframe(minmax_2, use_container_width=True)

    # =========================
    # DOWNLOAD
    # =========================
    output_file = "comparison_output.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        avg_table.to_excel(writer, sheet_name="Average", index=False)
        minmax_1.to_excel(writer, sheet_name=f"{company1}_MinMax", index=False)
        minmax_2.to_excel(writer, sheet_name=f"{company2}_MinMax", index=False)

    with open(output_file, "rb") as f:
        st.download_button("⬇️ Download Excel", f, file_name=output_file)