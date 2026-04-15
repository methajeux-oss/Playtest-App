import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Playstest App V1.8", layout="wide", page_icon="⚖️")

# 2. SESSION STATE FOR SETTINGS
if 'show_metrics' not in st.session_state:
    st.session_state.show_metrics = True
if 'show_charts' not in st.session_state:
    st.session_state.show_charts = True
if 'show_table' not in st.session_state:
    st.session_state.show_table = True

# 3. CSS STYLING
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.5rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        height: 45px; background-color: #1e1e1e; border-radius: 4px; padding: 10px; color: white; border: 1px solid #333;
    }
    .stTabs [aria-selected="true"] { background-color: #00d4ff !important; color: #0e1117 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 4. DATA CONFIGURATION
SCENARIO_GID = "0"
CAMPAIGN_GID = "718802502" 
BASE_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid="

@st.cache_data(ttl=300)
def load_all_data(source, is_scenario=True):
    try:
        df = pd.read_csv(source)
        df.columns = [str(c).strip() for c in df.columns]
        if df.empty: return pd.DataFrame()
        
        if is_scenario:
            df = df.dropna(subset=['Class', 'Date'])
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            num_cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            # --- CALCULATIONS ---
            # 1. Effort
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            
            # 2. Specialisation: Max value among D, H, M per row
            df['Specialisation'] = df[['Damage', 'Healing', 'Mitigation']].max(axis=1)
            
            # 3. Scenario Rank Logic
            df['session_id'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('session_id')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('session_id')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# 5. SIDEBAR
st.sidebar.header("📂 Data Connection")
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
    st.info("Please provide data to start the analysis.")
    st.stop()

# --- GLOBAL FILTERS ---
st.sidebar.divider()
classes = sorted(df_raw['Class'].unique())
class_a = st.sidebar.selectbox("Primary Class", classes)
compare_mode = st.sidebar.checkbox("Comparison Mode")
class_b = st.sidebar.selectbox("Secondary Class", [c for c in classes if c != class_a]) if compare_mode else None

level_filter = st.sidebar.selectbox("Level Filter (Metrics)", range(1, 10))
date_range = st.sidebar.date_input("Timeframe", [df_raw['Date'].min(), df_raw['Date'].max()])

# 6. TABS
tab_dash, tab_road, tab_settings = st.tabs(["📊 Analytic Dashboard", "🎯 Testing Roadmap", "⚙️ Settings"])

with tab_settings:
    st.header("Dashboard Configuration")
    st.write("Choose which elements to display on the main dashboard:")
    st.session_state.show_metrics = st.checkbox("Show Performance Metrics", value=st.session_state.show_metrics)
    st.session_state.show_charts = st.checkbox("Show Analysis Charts", value=st.session_state.show_charts)
    st.session_state.show_table = st.checkbox("Show Scenario Data Table", value=st.session_state.show_table)
    st.divider()
    st.write("System Status: Data Loaded ✅")

# 7. DATA PROCESSING (Filtering & Outliers)
def apply_filters(df, cls, lvl=None):
    mask = (df['Class'] == cls)
    if lvl: mask &= (df['Class Level'] == lvl)
    if len(date_range) == 2:
        mask &= (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
    return df[mask].copy()

# Data for Class A (Filtered by level) and All Levels (for Rank)
df_a = apply_filters(df_raw, class_a, level_filter)
df_a_all = apply_filters(df_raw, class_a) # All levels

# Data for Class B
df_b = apply_filters(df_raw, class_b, level_filter) if compare_mode else pd.DataFrame()
df_b_all = apply_filters(df_raw, class_b) if compare_mode else pd.DataFrame()

# Outlier Exclusion Logic
with st.expander("⚠️ Outlier Filtering"):
    df_pool = pd.concat([df_a, df_b])
    if len(df_pool) >= 4:
        Q1, Q3 = df_pool['Effort'].quantile(0.25), df_pool['Effort'].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df_pool[(df_pool['Effort'] < Q1 - 1.5*IQR) | (df_pool['Effort'] > Q3 + 1.5*IQR)].index.tolist()
        to_drop = st.multiselect("Exclude indices:", outliers, format_func=lambda x: f"[{df_pool.loc[x, 'Class']}] {df_pool.loc[x, 'Scenario']} ({df_pool.loc[x, 'Effort']})")
        df_a = df_a.drop([i for i in to_drop if i in df_a.index])
        if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])

with tab_dash:
    if df_a.empty:
        st.warning(f"No data for {class_a} at Level {level_filter}.")
    else:
        # --- METRICS SECTION ---
        if st.session_state.show_metrics:
            def render_class_metrics(df_filtered, df_full, name):
                st.subheader(f"Stats: {name} (Lvl {level_filter})")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Playtests", len(df_filtered))
                r2.metric("Avg Effort", f"{df_filtered['Effort'].mean():.1f}")
                r3.metric("Median Effort", f"{df_filtered['Effort'].median():.1f}")
                
                # Specialisation Calculation: mean/median of the row-wise max(D,H,M)
                avg_spec = df_filtered['Specialisation'].mean()
                r4.metric("Avg Specialisation", f"{avg_spec:.1f}")
                
                r5, r6, r7, r8 = st.columns(4)
                r5.metric("Median Specialisation", f"{df_filtered['Specialisation'].median():.1f}")
                r6.metric("Avg Hand", f"{df_filtered['In Hand'].mean():.1f}")
                r7.metric("Avg Discard", f"{df_filtered['Discard'].mean():.1f}")
                
                # Rank Calculation (Across all levels)
                avg_rank_global = df_full['Scenario Rank'].mean()
                r8.metric("Avg Rank (All Levels)", f"{avg_rank_global:.2f}")

            render_class_metrics(df_a, df_a_all, class_a)
            if compare_mode and not df_b.empty:
                st.divider()
                render_class_metrics(df_b, df_b_all, class_b)

        # --- CHARTS SECTION ---
        if st.session_state.show_charts:
            st.divider()
            c_rad, c_evol = st.columns([1, 2])
            with c_rad:
                st.subheader("Role Signature")
                radar_cols = ['Damage', 'Healing', 'Mitigation']
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
                if compare_mode and not df_b.empty:
                    fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
                fig_r.update_layout(polar=dict(radialaxis=dict(visible=True, gridcolor="#444")), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_r, use_container_width=True)
            
            with c_evol:
                st.subheader("Scientific Effort Modeling")
                df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
                fig_m = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State',
                                   trendline="ols", template="plotly_dark", hover_data=['Scenario', 'Rank String'])
                st.plotly_chart(fig_m, use_container_width=True)

        # --- TABLE SECTION ---
        if st.session_state.show_table:
            st.subheader("📋 Scenario Log")
            df_display = pd.concat([df_a, df_b]) if compare_mode else df_a
            cols = ['Date', 'Class', 'Scenario', 'Rank String', 'Effort', 'Specialisation', 'Damage', 'Healing', 'Mitigation', 'Result']
            st.dataframe(df_display[cols].sort_values('Date', ascending=False), use_container_width=True)

with tab_road:
    # (Roadmap features preserved from V1.9)
    st.header(f"Roadmap: {class_a}")
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty and 'Class' in df_campaigns.columns else 0
    st.metric("Total Campaign Tests", camp_count)
    
    # Coverage Chart Logic
    latest_state = df_a_all.sort_values('Date').iloc[-1]['Release State'] if not df_a_all.empty else "Alpha"
    target_max = 5 if str(latest_state).lower() == "alpha" else 9
    st.info(f"State: **{latest_state}**. Focus: Levels 1 to {target_max}.")
    
    cov_data = [{"Level": l, "Tests": len(df_a_all[df_a_all['Class Level'] == l])} for l in range(1, 10)]
    df_cov = pd.DataFrame(cov_data)
    fig_cov = px.bar(df_cov, x='Level', y='Tests', color=(df_cov['Level'] <= target_max), 
                     color_discrete_map={True: "#00d4ff", False: "#444444"}, title="Coverage Map")
    st.plotly_chart(fig_cov, use_container_width=True)
