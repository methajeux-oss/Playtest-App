import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V1.9", layout="wide", page_icon="⚖️")

# 2. CSS STYLING
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.6rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: #1e1e1e; border-radius: 4px; padding: 10px; color: white;
    }
    .stTabs [aria-selected="true"] { background-color: #00d4ff !important; color: #0e1117 !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. DATA SOURCE CONFIGURATION
SCENARIO_GID = "0"
CAMPAIGN_GID = "718802502" 
BASE_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid="

# 4. DATA ENGINE
@st.cache_data(ttl=300)
def load_all_data(source, is_scenario=True):
    try:
        df = pd.read_csv(source)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty: return pd.DataFrame()
        
        if is_scenario:
            df = df.dropna(subset=['Class', 'Date'])
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # Numeric cleaning
            num_cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            # 1. Effort Calculation
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            
            # 2. Scenario Rank Logic (Position in the group)
            # We group by Date and Scenario name to identify a single session
            df['session_id'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('session_id')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('session_id')['Class'].transform('count')
            df['Rank'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
            
        return df
    except Exception as e:
        st.error(f"Error loading: {e}")
        return pd.DataFrame()

# 5. SIDEBAR
st.sidebar.header("📂 Data Management")
data_mode = st.sidebar.radio("Source:", ["Google Sheets (Live)", "Manual Upload (CSV)"])

if data_mode == "Google Sheets (Live)":
    df_raw = load_all_data(BASE_URL + SCENARIO_GID)
    df_campaigns = load_all_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario CSV", type=['csv'])
    file_camp = st.sidebar.file_uploader("Upload Campaign CSV", type=['csv'])
    df_raw = load_all_data(file_scen) if file_scen else pd.DataFrame()
    df_campaigns = load_all_data(file_camp, is_scenario=False) if file_camp else pd.DataFrame()

if df_raw.empty:
    st.info("Waiting for data...")
    st.stop()

# --- FILTERS ---
st.sidebar.divider()
classes = sorted(df_raw['Class'].unique())
class_a = st.sidebar.selectbox("Primary Class", classes)
compare_mode = st.sidebar.checkbox("Comparison Mode")
class_b = st.sidebar.selectbox("Secondary Class", [c for c in classes if c != class_a]) if compare_mode else None

level_filter = st.sidebar.selectbox("Analysis Level", range(1, 10))
date_range = st.sidebar.date_input("Period", [df_raw['Date'].min(), df_raw['Date'].max()])

# Sidebar diversity
class_a_all = df_raw[df_raw['Class'] == class_a]
st.sidebar.metric("Unique Testers", class_a_all['Played By'].nunique())

# 6. FILTERING & OUTLIERS
def apply_filters(df, cls):
    mask = (df['Class'] == cls) & (df['Class Level'] == level_filter)
    if len(date_range) == 2:
        mask &= (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
    return df[mask].copy()

df_a = apply_filters(df_raw, class_a)
df_b = apply_filters(df_raw, class_b) if compare_mode else pd.DataFrame()

with st.expander("⚠️ Outlier & Data Cleaning"):
    df_clean_pool = pd.concat([df_a, df_b])
    if len(df_clean_pool) >= 4:
        Q1, Q3 = df_clean_pool['Effort'].quantile(0.25), df_clean_pool['Effort'].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df_clean_pool[(df_clean_pool['Effort'] < Q1 - 1.5*IQR) | (df_clean_pool['Effort'] > Q3 + 1.5*IQR)].index.tolist()
        
        to_drop = st.multiselect("Exclude from analysis:", outliers, 
                                format_func=lambda x: f"[{df_clean_pool.loc[x, 'Class']}] {df_clean_pool.loc[x, 'Date'].date()} - {df_clean_pool.loc[x, 'Scenario']} (Effort: {df_clean_pool.loc[x, 'Effort']})")
        df_a = df_a.drop([i for i in to_drop if i in df_a.index])
        if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])
    else:
        st.write("Not enough data for automatic outlier detection.")

# 7. TABS
tab_dash, tab_road = st.tabs(["📊 Analytics Dashboard", "🎯 Testing Roadmap"])

with tab_dash:
    if df_a.empty:
        st.warning("No data for these filters.")
    else:
        # --- METRICS ---
        def metrics_row(df, label):
            st.markdown(f"**{label}**")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Playtests", len(df))
            m2.metric("Avg Effort", f"{df['Effort'].mean():.1f}")
            m3.metric("Avg Damage", f"{df['Damage'].mean():.1f}")
            m4.metric("Avg Sustain", f"{(df['Healing'] + df['Mitigation']).mean():.1f}")
            m5.metric("Avg Rank", f"{df['Scenario Rank'].mean():.1f}")

        metrics_row(df_a, class_a)
        if compare_mode and not df_b.empty:
            st.divider()
            metrics_row(df_b, class_b)

        st.divider()
        col_rad, col_model = st.columns([1, 2])
        
        with col_rad:
            st.subheader("Role Signature")
            radar_cols = ['Damage', 'Healing', 'Mitigation']
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
            if compare_mode and not df_b.empty:
                fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, gridcolor="#444")), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_r, use_container_width=True)

        with col_model:
            st.subheader("Scientific Modeling (Effort Curve)")
            df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
            # Modeling using OLS trendline for scientific look
            fig_m = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State',
                               trendline="ols", # Ordinary Least Squares for scientific modeling
                               template="plotly_dark",
                               hover_data=['Scenario', 'Rank', 'Played By'])
            fig_m.update_traces(marker=dict(size=10, opacity=0.7, line=dict(width=1, color='White')))
            st.plotly_chart(fig_m, use_container_width=True)

        # --- THE RESTORED TABLE (SCENARIO LOG) ---
        st.subheader("📋 Detailed Scenario Log")
        st.info("This table reflects your filters and outlier exclusions.")
        display_cols = ['Date', 'Class', 'Scenario', 'Rank', 'Effort', 'Damage', 'Healing', 'Mitigation', 'In Hand', 'Discard', 'Result', 'Played By']
        st.dataframe(df_plot[display_cols].sort_values('Date', ascending=False), use_container_width=True)

with tab_road:
    st.header(f"Roadmap: {class_a}")
    
    # Campaign Counter
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty and 'Class' in df_campaigns.columns else 0
    st.metric("Total Campaign Tests", camp_count)
    
    # Roadmap Logic
    latest_state = class_a_all.sort_values('Date').iloc[-1]['Release State'] if not class_a_all.empty else "Alpha"
    target_max = 5 if str(latest_state).lower() == "alpha" else 9
    st.info(f"State: **{latest_state}**. Focus: Levels 1 to {target_max}.")
    
    # Coverage Chart
    cov_data = [{"Level": l, "Tests": len(class_a_all[class_a_all['Class Level'] == l])} for l in range(1, 10)]
    df_cov = pd.DataFrame(cov_data)
    df_cov['Priority'] = df_cov['Level'].apply(lambda x: "Target" if x <= target_max else "Optional")
    
    fig_cov = px.bar(df_cov, x='Level', y='Tests', color='Priority', 
                     color_discrete_map={"Target": "#00d4ff", "Optional": "#444444"},
                     title="Data Coverage by Level")
    st.plotly_chart(fig_cov, use_container_width=True)
    
    # Recommendations
    missing = [r['Level'] for i, r in df_cov.iterrows() if r['Tests'] == 0 and r['Level'] <= target_max]
    if missing:
        st.error(f"🚨 Missing data for levels: {missing}")
    else:
        st.success("✅ Target coverage achieved for current state.")

    # Campaign History Table
    if not df_campaigns.empty and 'Class' in df_campaigns.columns:
        st.divider()
        st.subheader("Campaign History Details")
        st.dataframe(df_campaigns[df_campaigns['Class'] == class_a], use_container_width=True)
