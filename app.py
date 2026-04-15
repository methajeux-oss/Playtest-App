import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V2.1", layout="wide", page_icon="⚖️")

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
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.4rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; }
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
            
            # CALCULATIONS
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['session_id'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('session_id')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('session_id')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
            
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# 5. SIDEBAR
st.sidebar.header("📂 Data Source")
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
    st.stop()

# --- FILTERS ---
st.sidebar.divider()
classes = sorted(df_raw['Class'].unique())
class_a = st.sidebar.selectbox("Primary Class", classes)
compare_mode = st.sidebar.checkbox("Comparison Mode")
class_b = st.sidebar.selectbox("Secondary Class", [c for c in classes if c != class_a]) if compare_mode else None

level_filter = st.sidebar.selectbox("Level Filter", range(1, 10))
date_range = st.sidebar.date_input("Period", [df_raw['Date'].min(), df_raw['Date'].max()])

# 6. PROCESSING
def filter_data(df, cls, lvl=None):
    mask = (df['Class'] == cls)
    if lvl: mask &= (df['Class Level'] == lvl)
    if len(date_range) == 2:
        mask &= (df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])
    return df[mask].copy()

df_a = filter_data(df_raw, class_a, level_filter)
df_a_all = filter_data(df_raw, class_a)
df_b = filter_data(df_raw, class_b, level_filter) if compare_mode else pd.DataFrame()
df_b_all = filter_data(df_raw, class_b) if compare_mode else pd.DataFrame()

# Outliers
with st.expander("⚠️ Outlier Management"):
    df_pool = pd.concat([df_a, df_b])
    if len(df_pool) >= 4:
        Q1, Q3 = df_pool['Effort'].quantile(0.25), df_pool['Effort'].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df_pool[(df_pool['Effort'] < Q1 - 1.5*IQR) | (df_pool['Effort'] > Q3 + 1.5*IQR)].index.tolist()
        to_drop = st.multiselect("Exclude:", outliers, format_func=lambda x: f"{df_pool.loc[x, 'Scenario']} ({df_pool.loc[x, 'Effort']})")
        df_a = df_a.drop([i for i in to_drop if i in df_a.index])
        if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])

# 7. TABS
tab_dash, tab_road, tab_settings = st.tabs(["📊 Analytic Dashboard", "🎯 Testing Roadmap", "⚙️ Settings"])

with tab_settings:
    st.header("Dashboard Settings")
    st.session_state.show_metrics = st.checkbox("Show Metrics", value=st.session_state.show_metrics)
    st.session_state.show_charts = st.checkbox("Show Charts", value=st.session_state.show_charts)
    st.session_state.show_table = st.checkbox("Show Log Table", value=st.session_state.show_table)

with tab_dash:
    if df_a.empty:
        st.warning("No data found.")
    else:
        if st.session_state.show_metrics:
            def render_metrics(df, df_full, name):
                st.subheader(f"Results: {name} (Lvl {level_filter})")
                # Row 1: General & Effort
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Playtests", len(df))
                c2.metric("Unique Testers", df['Played By'].nunique())
                c3.metric("Avg Effort", f"{df['Effort'].mean():.1f}")
                c4.metric("Median Effort", f"{df['Effort'].median():.1f}")
                
                # Row 2: Damage & Healing
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Avg Damage", f"{df['Damage'].mean():.1f}")
                c6.metric("Median Damage", f"{df['Damage'].median():.1f}")
                c7.metric("Avg Healing", f"{df['Healing'].mean():.1f}")
                c8.metric("Median Healing", f"{df['Healing'].median():.1f}")
                
                # Row 3: Mitigation & Rank
                c9, c10, c11, c12 = st.columns(4)
                c9.metric("Avg Mitigation", f"{df['Mitigation'].mean():.1f}")
                c10.metric("Median Mitigation", f"{df['Mitigation'].median():.1f}")
                c11.metric("Avg Hand", f"{df['In Hand'].mean():.1f}")
                # Note: Global rank (all levels) as requested
                c12.metric("Avg Rank (Global)", f"{df_full['Scenario Rank'].mean():.2f}")
                
                # Row 4: Hand Mgmt
                c13, c14, _, _ = st.columns(4)
                c13.metric("Avg Discard", f"{df['Discard'].mean():.1f}")

            render_metrics(df_a, df_a_all, class_a)
            if compare_mode and not df_b.empty:
                st.divider()
                render_metrics(df_b, df_b_all, class_b)

        if st.session_state.show_charts:
            st.divider()
            c_rad, c_evol = st.columns([1, 2])
            with c_rad:
                radar_cols = ['Damage', 'Healing', 'Mitigation']
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
                if compare_mode and not df_b.empty:
                    fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
                fig_r.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark", showlegend=True)
                st.plotly_chart(fig_r, use_container_width=True)
            
            with c_evol:
                df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
                fig_m = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State', trendline="ols", template="plotly_dark")
                st.plotly_chart(fig_m, use_container_width=True)

        if st.session_state.show_table:
            st.subheader("📋 Scenario Log")
            df_display = pd.concat([df_a, df_b]) if compare_mode else df_a
            cols = ['Date', 'Class', 'Scenario', 'Rank String', 'Effort', 'Damage', 'Healing', 'Mitigation', 'In Hand', 'Discard', 'Result']
            st.dataframe(df_display[cols].sort_values('Date', ascending=False), use_container_width=True)

with tab_road:
    st.header(f"Roadmap: {class_a}")
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty and 'Class' in df_campaigns.columns else 0
    st.metric("Total Campaign Tests", camp_count)
    
    latest_state = df_a_all.sort_values('Date').iloc[-1]['Release State'] if not df_a_all.empty else "Alpha"
    target_max = 5 if str(latest_state).lower() == "alpha" else 9
    st.info(f"Current State: {latest_state} (Target: Levels 1-{target_max})")
    
    cov_data = [{"Level": l, "Tests": len(df_a_all[df_a_all['Class Level'] == l])} for l in range(1, 10)]
    fig_cov = px.bar(pd.DataFrame(cov_data), x='Level', y='Tests', color_discrete_sequence=['#00d4ff'], title="Coverage Chart")
    st.plotly_chart(fig_cov, use_container_width=True)
