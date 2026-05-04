from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path for imports to work when running streamlit
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import GOLD_PATH, MODELS_PATH, SILVER_PATH

# Page configuration
st.set_page_config(
    page_title="Grocery Sales Analytics Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
        .metric-card {
            background-color: #f0f2f6;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .header-section {
            padding: 20px 0;
            border-bottom: 3px solid #1f77b4;
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown("<h1 style='text-align: center; color: #1f77b4;'>📊 Grocery Sales Analytics Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Data Pipeline: Bronze → Silver → Gold → ML Training</p>", unsafe_allow_html=True)

# Load data
if not SILVER_PATH.exists():
    st.error("❌ Silver layer is missing. Run the ETL jobs first.")
    st.stop()

silver = pd.read_parquet(SILVER_PATH)
metrics_path = MODELS_PATH / "metrics.json"
metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}

# Sidebar filters
st.sidebar.markdown("### 🔍 Filters")

# Filter by Item Type
item_types = sorted(silver["item_type"].unique())
selected_items = st.sidebar.multiselect(
    "Item Type",
    options=item_types,
    default=item_types,
    help="Select one or more item types to filter"
)

# Filter by Outlet Type
outlet_types = sorted(silver["outlet_type"].unique())
selected_outlets = st.sidebar.multiselect(
    "Outlet Type",
    options=outlet_types,
    default=outlet_types,
    help="Select one or more outlet types to filter"
)

# Filter by Location Type
location_types = sorted(silver["outlet_location_type"].unique())
selected_locations = st.sidebar.multiselect(
    "Location Type",
    options=location_types,
    default=location_types,
    help="Select one or more location types to filter"
)

# Filter by Outlet Size
outlet_sizes = sorted(silver["outlet_size"].unique())
selected_sizes = st.sidebar.multiselect(
    "Outlet Size",
    options=outlet_sizes,
    default=outlet_sizes,
    help="Select one or more outlet sizes to filter"
)

# Filter by Fat Content
fat_contents = sorted(silver["item_fat_content"].unique())
selected_fats = st.sidebar.multiselect(
    "Item Fat Content",
    options=fat_contents,
    default=fat_contents,
    help="Select one or more fat content types to filter"
)

# Sales range slider
sales_min, sales_max = float(silver["total_sales"].min()), float(silver["total_sales"].max())
selected_sales_range = st.sidebar.slider(
    "Sales Range ($)",
    min_value=sales_min,
    max_value=sales_max,
    value=(sales_min, sales_max),
    step=10.0,
    help="Filter by sales amount range"
)

# Apply filters
filtered_data = silver[
    (silver["item_type"].isin(selected_items)) &
    (silver["outlet_type"].isin(selected_outlets)) &
    (silver["outlet_location_type"].isin(selected_locations)) &
    (silver["outlet_size"].isin(selected_sizes)) &
    (silver["item_fat_content"].isin(selected_fats)) &
    (silver["total_sales"] >= selected_sales_range[0]) &
    (silver["total_sales"] <= selected_sales_range[1])
]

# Reset filters button
if st.sidebar.button("🔄 Reset All Filters", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(f"📈 **Records after filter:** {len(filtered_data):,} / {len(silver):,}")

# Key Metrics Section
st.markdown("### 📊 Key Performance Indicators")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Records", f"{len(filtered_data):,}", f"{len(filtered_data) - len(silver)} from orig.", delta_color="off")
with col2:
    avg_sales = filtered_data["total_sales"].mean()
    st.metric("Avg Sales ($)", f"{avg_sales:,.2f}", f"{avg_sales - silver['total_sales'].mean():.2f}")
with col3:
    total_sales = filtered_data["total_sales"].sum()
    st.metric("Total Sales ($)", f"{total_sales:,.0f}", f"{total_sales - silver['total_sales'].sum():.0f}")
with col4:
    avg_rating = filtered_data["rating"].mean()
    st.metric("Avg Rating", f"{avg_rating:.2f} ⭐", "out of 5")
with col5:
    st.metric("Model R² Score", f"{metrics.get('r2', 0):.3f}", "Test Performance", delta_color="off")

st.markdown("---")

# Visualizations - Two columns layout
col_left, col_right = st.columns(2)

# 1. Sales by Item Type (Bar Chart)
with col_left:
    st.markdown("#### 📦 Sales by Item Type")
    item_sales = filtered_data.groupby("item_type", as_index=False).agg({
        "total_sales": ["sum", "count", "mean"]
    }).round(2)
    item_sales.columns = ["Item Type", "Total Sales", "Count", "Avg Sales"]
    item_sales = item_sales.sort_values("Total Sales", ascending=False)
    
    fig = px.bar(
        item_sales,
        x="Item Type",
        y="Total Sales",
        color="Avg Sales",
        color_continuous_scale="Blues",
        hover_data={"Count": True, "Avg Sales": ":.2f"},
        labels={"Total Sales": "Total Sales ($)", "Item Type": "Product Type"}
    )
    fig.update_layout(hovermode="x unified", showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)

# 2. Outlet Performance (Pie Chart)
with col_right:
    st.markdown("#### 🏪 Sales Distribution by Outlet Type")
    outlet_sales = filtered_data.groupby("outlet_type", as_index=False)["total_sales"].sum()
    
    fig = px.pie(
        outlet_sales,
        names="outlet_type",
        values="total_sales",
        color_discrete_sequence=px.colors.sequential.Blues,
        labels={"outlet_type": "Outlet Type", "total_sales": "Sales ($)"}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# 3. Sales Distribution (Histogram)
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 📈 Sales Amount Distribution")
    fig = px.histogram(
        filtered_data,
        x="total_sales",
        nbins=50,
        color_discrete_sequence=["#1f77b4"],
        labels={"total_sales": "Sales ($)"}
    )
    fig.update_layout(showlegend=False, hovermode="x unified", height=400)
    st.plotly_chart(fig, use_container_width=True)

# 4. Location Performance (Horizontal Bar)
with col_right:
    st.markdown("#### 🗺️ Sales by Location Type")
    location_sales = filtered_data.groupby("outlet_location_type", as_index=False).agg({
        "total_sales": ["sum", "count"]
    }).round(0)
    location_sales.columns = ["Location Type", "Total Sales", "Count"]
    location_sales = location_sales.sort_values("Total Sales", ascending=True)
    
    fig = px.bar(
        location_sales,
        y="Location Type",
        x="Total Sales",
        color="Total Sales",
        color_continuous_scale="Blues",
        orientation="h",
        hover_data={"Count": True},
        labels={"Total Sales": "Sales ($)", "Location Type": "Location Tier"}
    )
    fig.update_layout(showlegend=False, height=300)
    st.plotly_chart(fig, use_container_width=True)

# 5. Outlet Size Performance (Box Plot)
st.markdown("#### 📊 Sales Distribution by Outlet Size")
fig = px.box(
    filtered_data,
    x="outlet_size",
    y="total_sales",
    color="outlet_size",
    color_discrete_sequence=px.colors.qualitative.Set2,
    labels={"outlet_size": "Outlet Size", "total_sales": "Sales ($)"},
    points="outliers"
)
fig.update_layout(hovermode="x unified", showlegend=False, height=400)
st.plotly_chart(fig, use_container_width=True)

# 6. Item Fat Content Performance
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### 🥗 Sales by Fat Content")
    fat_sales = filtered_data.groupby("item_fat_content", as_index=False).agg({
        "total_sales": ["sum", "mean", "count"]
    }).round(2)
    fat_sales.columns = ["Fat Content", "Total Sales", "Avg Sales", "Count"]
    
    fig = px.bar(
        fat_sales,
        x="Fat Content",
        y="Total Sales",
        color="Avg Sales",
        color_continuous_scale="RdYlGn",
        hover_data={"Count": True, "Avg Sales": ":.2f"}
    )
    fig.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig, use_container_width=True)

# 7. Outlet Establishment Year Trend (if data spans multiple years)
with col_right:
    st.markdown("#### 📅 Sales Trend by Outlet Age")
    year_sales = filtered_data.groupby("outlet_establishment_year", as_index=False).agg({
        "total_sales": ["sum", "count"]
    }).round(0)
    year_sales.columns = ["Year", "Total Sales", "Count"]
    year_sales = year_sales.sort_values("Year")
    
    fig = px.line(
        year_sales,
        x="Year",
        y="Total Sales",
        markers=True,
        color_discrete_sequence=["#1f77b4"],
        hover_data={"Count": True}
    )
    fig.update_layout(showlegend=False, height=350, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# 8. Top Products Table
st.markdown("#### 🏆 Top 10 Best Performing Products (by Total Sales)")
top_products = filtered_data.groupby("item_identifier", as_index=False).agg({
    "item_type": "first",
    "total_sales": "sum",
    "rating": "mean",
    "item_identifier": "count"
}).rename(columns={"item_identifier": "Product ID", "item_type": "Category", "total_sales": "Total Sales", "rating": "Avg Rating", "item_identifier": "Count"})

top_products = filtered_data.groupby(["item_identifier", "item_type"], as_index=False).agg({
    "total_sales": "sum",
    "rating": "mean"
}).rename(columns={"item_identifier": "Product ID", "item_type": "Category", "total_sales": "Total Sales", "rating": "Avg Rating"})
top_products = top_products.sort_values("Total Sales", ascending=False).head(10)

# Format the table
top_products["Total Sales"] = top_products["Total Sales"].apply(lambda x: f"${x:,.2f}")
top_products["Avg Rating"] = top_products["Avg Rating"].apply(lambda x: f"{x:.2f} ⭐")

st.dataframe(top_products, use_container_width=True, hide_index=True)

# Gold Layer Preview
st.markdown("---")
st.markdown("#### 🗄️ Warehouse Gold Layer Preview")
gold_fact_path = GOLD_PATH / "fact_sales"
if gold_fact_path.exists():
    gold_fact = pd.read_parquet(gold_fact_path)
    st.info(f"📦 Gold Layer contains {len(gold_fact):,} fact records and 3 dimension tables (item, outlet, date)")
    st.dataframe(gold_fact.head(10), use_container_width=True)
else:
    st.warning("⚠️ Gold fact table not found. Run the Gold layer build step to populate the warehouse.")

# Filtered Dataset Explorer
st.markdown("---")
st.markdown("#### 📋 Filtered Dataset Explorer")

# Create tabs for different views
tab1, tab2, tab3 = st.tabs(["📊 Data Table", "📈 Column Statistics", "🔍 Sample Records"])

with tab1:
    st.markdown("**Showing filtered data with all columns**")
    
    # Display controls
    col_left, col_right = st.columns(2)
    with col_left:
        rows_to_show = st.selectbox(
            "Rows to display",
            options=[10, 25, 50, 100, len(filtered_data)],
            index=1,
            help="Select how many rows to display"
        )
    with col_right:
        sort_column = st.selectbox(
            "Sort by column",
            options=filtered_data.columns,
            index=list(filtered_data.columns).index("total_sales"),
            help="Select column to sort by"
        )
    
    # Sort and display
    sorted_data = filtered_data.sort_values(by=sort_column, ascending=False)
    display_data = sorted_data.head(rows_to_show).copy()
    
    # Format numeric columns
    for col in display_data.select_dtypes(include=['float64']).columns:
        display_data[col] = display_data[col].round(2)
    
    st.dataframe(
        display_data,
        use_container_width=True,
        height=400,
        column_config={
            "total_sales": st.column_config.NumberColumn("Sales ($)", format="$%.2f"),
            "item_visibility": st.column_config.NumberColumn("Visibility", format="%.4f"),
            "item_weight": st.column_config.NumberColumn("Weight (kg)", format="%.2f"),
            "rating": st.column_config.NumberColumn("Rating", format="%.2f ⭐"),
        }
    )
    
    st.caption(f"Showing {min(rows_to_show, len(filtered_data))} of {len(filtered_data):,} filtered records")

with tab2:
    st.markdown("**Statistical Summary of Filtered Data**")
    
    # Numeric columns stats
    numeric_cols = filtered_data.select_dtypes(include=['float64', 'int64']).columns
    stats_data = filtered_data[numeric_cols].describe().round(2)
    
    # Create two columns for stats
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Numeric Column Statistics")
        st.dataframe(stats_data, use_container_width=True)
    
    with col_right:
        st.subheader("Categorical Distribution")
        categorical_cols = ["item_type", "outlet_type", "outlet_location_type", "outlet_size", "item_fat_content"]
        selected_cat = st.selectbox("Select categorical column", options=categorical_cols)
        
        cat_dist = filtered_data[selected_cat].value_counts()
        fig = px.pie(
            values=cat_dist.values,
            names=cat_dist.index,
            title=f"Distribution of {selected_cat}",
            color_discrete_sequence=px.colors.sequential.Blues
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("**Sample Records from Filtered Dataset**")
    
    # Random sample selector
    sample_size = st.slider("Sample size", min_value=5, max_value=min(50, len(filtered_data)), value=10)
    
    if len(filtered_data) > 0:
        sample_data = filtered_data.sample(n=min(sample_size, len(filtered_data)), random_state=42).copy()
        
        # Format for display
        for col in sample_data.select_dtypes(include=['float64']).columns:
            sample_data[col] = sample_data[col].round(2)
        
        st.dataframe(sample_data, use_container_width=True)
        
        # Summary statistics of sample
        st.subheader("Sample Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sample Avg Sales", f"${sample_data['total_sales'].mean():.2f}")
        with col2:
            st.metric("Sample Max Sales", f"${sample_data['total_sales'].max():.2f}")
        with col3:
            st.metric("Sample Min Sales", f"${sample_data['total_sales'].min():.2f}")
        with col4:
            st.metric("Sample Avg Rating", f"{sample_data['rating'].mean():.2f} ⭐")
    else:
        st.warning("No data matches the selected filters.")
