import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V1.5", layout="wide", page_icon="⚖️")

# 2. DARK MODE STYLE AND METRICS
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.8rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTable { background-color: #1e1e1e; }
    [data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 3. GOOGLE SHEETS CONFIGURATION
# Permanent link transformed to direct CSV export URL
GSHEET_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv"

# 4. DATA LOADING AND CLEANING
@st.cache_data(ttl=600) # Refresh data every 10 minutes if using Google Sheet
def load_data(source):
    try:
        df = pd.read_csv(source)
        # Basic cleaning
        df = df.dropna(subset=['Class', 'Date'])
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Numeric conversion for all metrics
        numeric_cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard', 'Effort']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Force Effort Recalculation: Damage + (Healing + Mitigation) * 0.75
        df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def detect_outliers(df, column):
    """Interquartile Range (IQR) algorithm to detect statistical anomalies."""
    if df.empty or len(df) < 4: return []
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] < lower_bound) | (df[column] > upper_bound)].index.tolist()

# 5. HEADER
st.title("🛡️ Frosthaven Class Lab: Comprehensive Analyzer")

# 6. SIDEBAR: SOURCE AND FILTERS
st.sidebar.header("⚙️ Data Source")
data_source = st.sidebar.radio("Select Source:", ["Live Google Sheet", "Manual CSV Upload"])

df_raw = pd.DataFrame()

if data_source == "Live Google Sheet":
    df_raw = load_data(GSHEET_URL)
    st.sidebar.success("Connected to Google Drive")
else:
    uploaded_file = st.sidebar.file_uploader("Upload local CSV", type=['csv'])
    if uploaded_file:
        df_raw = load_data(uploaded_file)

if not df_raw.empty:
    st.sidebar.divider()
    st.sidebar.header("🎯 Filters")
    
    # Class Selection
    class_list = sorted(df_raw['Class'].unique())
    classe_a = st.sidebar.selectbox("Primary Class", class_list)
    
    # Comparison Mode
    comparaison_on = st.sidebar.checkbox("Enable Comparison Mode")
    classe_b = None
    if comparaison_on:
        classe_b = st.sidebar.selectbox("Class to Compare", [c for c in class_list if c != classe_a])

    # Level Filter
    level_selected = st.sidebar.selectbox("Test Level", range(1, 10))

    # Calendar Filter
    min_date = df_raw['Date'].min().to_pydatetime()
    max_date = df_raw['Date'].max().to_pydatetime()
    date_range = st.sidebar.date_input("Analysis Period", [min_date, max_date])

    # --- DATA FILTERING LOGIC ---
    def filter_class_data(cls, lvl, dates):
        mask = (df_raw['Class'] == cls) & (df_raw['Class Level'] == lvl)
        if len(dates) == 2:
            mask &= (df_raw['Date'].dt.date >= dates[0]) & (df_raw['Date'].dt.date <= dates[1])
        return df_raw[mask].copy()

    df_a = filter_class_data(classe_a, level_selected, date_range)
    
    if df_a.empty:
        st.warning(f"No data found for {classe_a} at level {level_selected} for the selected dates.")
    else:
        # --- OUTLIER MANAGEMENT ---
        df_to_check = df_a.copy()
        if comparaison_on and classe_b:
            df_b_temp = filter_class_data(classe_b, level_selected, date_range)
            df_to_check = pd.concat([df_a, df_b_temp])

        outlier_indices = detect_outliers(df_to_check, 'Effort')

        with st.expander("⚠️ Outlier Management"):
            if outlier_indices:
                st.write("Anomalies detected based on Effort score:")
                to_exclude = st.multiselect(
                    "Select rows to exclude from analysis:",
                    outlier_indices,
                    format_func=lambda x: f"[{df_to_check.loc[x, 'Class']}] {df_to_check.loc[x, 'Date'].date()} - Scen: {df_to_check.loc[x, 'Scenario']} (Effort: {df_to_check.loc[x, 'Effort']})"
                )
                if to_exclude:
                    df_a = df_a.drop([i for i in to_exclude if i in df_a.index])
                    st.info(f"Updated: {len(to_exclude)} tests excluded.")
            else:
                st.success("No statistical anomalies detected.")

        # Prepare Class B after potential exclusions
        df_b = pd.DataFrame()
        if comparaison_on and classe_b:
            df_b = filter_class_data(classe_b, level_selected, date_range)
            if outlier_indices:
                df_b = df_b.drop([i for i in to_exclude if i in df_b.index])

        # --- PERFORMANCE METRICS ---
        def display_class_metrics(df_target, name):
            st.subheader(f"📊 Statistics: {name}")
            # Group 1: Combat
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Playtests", len(df_target))
            c2.metric("Damage (Avg)", f"{df_target['Damage'].mean():.1f}")
            c3.metric("Healing (Avg)", f"{df_target['Healing'].mean():.1f}")
            c4.metric("Mitigation (Avg)", f"{df_target['Mitigation'].mean():.1f}")
            c5.metric("AVG EFFORT", f"{df_target['Effort'].mean():.1f}")
            
            # Group 2: Hand/Longevity
            st.markdown(f"*Sustainability metrics for {name}:*")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Hand (Avg)", f"{df_target['In Hand'].mean():.1f}")
            m2.metric("Hand (Med)", f"{df_target['In Hand'].median():.1f}")
            m3.metric("Discard (Avg)", f"{df_target['Discard'].mean():.1f}")
            m4.metric("Discard (Med)", f"{df_target['Discard'].median():.1f}")

        display_class_metrics(df_a, classe_a)
        if comparaison_on and not df_b.empty:
            st.divider()
            display_class_metrics(df_b, classe_b)

        st.divider()

        # --- VISUALIZATIONS ---
        col_radar, col_evol = st.columns([1, 2])

        with col_radar:
            st.subheader("🎯 Role Radar")
            categories = ['Damage', 'Healing', 'Mitigation']
            fig_radar = go.Figure()
            
            # Primary Class Trace
            fig_radar.add_trace(go.Scatterpolar(
                r=[df_a['Damage'].mean(), df_a['Healing'].mean(), df_a['Mitigation'].mean()],
                theta=categories, fill='toself', name=classe_a, line_color='#00d4ff'
            ))
            
            # Comparison Class Trace
            if comparaison_on and not df_b.empty:
                fig_radar.add_trace(go.Scatterpolar(
                    r=[df_b['Damage'].mean(), df_b['Healing'].mean(), df_b['Mitigation'].mean()],
                    theta=categories, fill='toself', name=classe_b, line_color='#ff4b4b'
                ))
            
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, gridcolor="#444")),
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=True
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_evol:
            st.subheader("📈 Power Curve (Lowess Modeling)")
            df_plot = df_a.copy()
            if comparaison_on and not df_b.empty:
                df_plot = pd.concat([df_a, df_b])
            
            fig_evol = px.scatter(
                df_plot, x='Date', y='Effort', color='Class' if comparaison_on else 'Release State',
                trendline="lowess",
                title="Evolution of Performance over Time",
                template="plotly_dark",
                hover_data=['Scenario', 'Played By', 'Damage', 'Result']
            )
            st.plotly_chart(fig_evol, use_container_width=True)

        # --- DATA LOG ---
        st.subheader("📋 Detailed Scenario Log")
        cols_to_show = ['Date', 'Class', 'Release State', 'Scenario', 'Damage', 'Healing', 'Mitigation', 'Effort', 'In Hand', 'Discard', 'Result']
        st.dataframe(df_plot[cols_to_show].sort_values('Date', ascending=False), use_container_width=True)

else:
    st.info("Please select 'Live Google Sheet' or upload a CSV file to begin analysis.")
