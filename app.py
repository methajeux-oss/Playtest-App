import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V2.4", layout="wide", page_icon="🛡️")

# 2. ICON CONFIGURATION
# Using RAW content URL for GitHub
GITHUB_ICON_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/"

def get_icon_url(class_name):
    if pd.isna(class_name) or class_name == "":
        return ""
    # Standardizing filename: trim and replace spaces
    clean_name = str(class_name).strip().replace(" ", "%20")
    return f"{GITHUB_ICON_BASE}{clean_name}.png"

# 3. SESSION STATE
if 'show_metrics' not in st.session_state: st.session_state.show_metrics = True
if 'show_charts' not in st.session_state: st.session_state.show_charts = True
if 'show_table' not in st.session_state: st.session_state.show_table = True

# 4. CSS FOR THEME & ICON ALIGNMENT
st.markdown("""
    <style>
    /* Dynamic Metric Color */
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.4rem; }
    
    /* Forced Icon Size for Headers */
    .icon-container {
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border-radius: 8px;
        background-color: rgba(127, 127, 127, 0.1);
    }
    .icon-container img {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    </style>
    """, unsafe_allow_html=True)

# 5. DATA ENGINE
SCENARIO_GID = "0"
CAMPAIGN_GID = "718802502" 
BASE_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid="

@st.cache_data(ttl=300)
def load_data(source, is_scenario=True):
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
            
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['Icon URL'] = df['Class'].apply(get_icon_url)
            
            # Scenario Rank Logic
            df['sid'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('sid')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
            
        return df
    except Exception as e:
        st.error(f"Data Loading Error: {e}")
        return pd.DataFrame()

# 6. SIDEBAR
st.sidebar.header("📂 Data Connection")
data_mode = st.sidebar.radio("Source:", ["Google Sheets (Live)", "Manual Upload"])

if data_mode == "Google Sheets (Live)":
    df_raw = load_data(BASE_URL + SCENARIO_GID)
    df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario CSV", type=['csv'])
    df_raw = load_data(file_scen) if file_scen else pd.DataFrame()
    df_campaigns = pd.DataFrame()

if df_raw.empty:
    st.info("Awaiting data...")
    st.stop()

# --- FILTERS ---
unique_classes = df_raw['Class'].dropna().unique()
classes = sorted([str(c) for c in unique_classes])

class_a = st.sidebar.selectbox("Primary Class", classes)
st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_a)}"></div>', unsafe_allow_html=True)

compare_mode = st.sidebar.checkbox("Comparison Mode")
class_b = st.sidebar.selectbox("Secondary Class", [c for c in classes if c != class_a]) if compare_mode else None
if compare_mode: 
    st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_b)}"></div>', unsafe_allow_html=True)

level_filter = st.sidebar.selectbox("Analysis Level", range(1, 10))
date_range = st.sidebar.date_input("Timeframe", [df_raw['Date'].min(), df_raw['Date'].max()])

# 7. PROCESSING
def get_filtered(cls, lvl=None):
    mask = (df_raw['Class'] == cls)
    if lvl: mask &= (df_raw['Class Level'] == lvl)
    if len(date_range) == 2:
        mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
    return df_raw[mask].copy()

df_a = get_filtered(class_a, level_filter)
df_a_all = get_filtered(class_a)
df_b = get_filtered(class_b, level_filter) if compare_mode else pd.DataFrame()
df_b_all = get_filtered(class_b) if compare_mode else pd.DataFrame()

# Outlier Management
with st.expander("⚠️ Outlier Filtering"):
    df_pool = pd.concat([df_a, df_b])
    if len(df_pool) >= 4:
        Q1, Q3 = df_pool['Effort'].quantile(0.25), df_pool['Effort'].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df_pool[(df_pool['Effort'] < Q1 - 1.5*IQR) | (df_pool['Effort'] > Q3 + 1.5*IQR)].index.tolist()
        to_drop = st.multiselect("Exclude from analysis:", outliers, format_func=lambda x: f"{df_pool.loc[x, 'Scenario']} (Effort: {df_pool.loc[x, 'Effort']})")
        df_a = df_a.drop([i for i in to_drop if i in df_a.index])
        if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])

# 8. TABS
tab_dash, tab_road, tab_settings = st.tabs(["📊 Analytics Dashboard", "🎯 Testing Roadmap", "⚙️ Settings"])

with tab_dash:
    if df_a.empty:
        st.warning("No data found for the selected level.")
    else:
        if st.session_state.show_metrics:
            def render_full_metrics(df, df_full, name):
                col_img, col_txt = st.columns([1, 12])
                with col_img: 
                    st.markdown(f'<div class="icon-container"><img src="{get_icon_url(name)}"></div>', unsafe_allow_html=True)
                with col_txt: st.subheader(f"Stats: {name} (Level {level_filter})")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Playtests", len(df))
                c2.metric("Unique Testers", df['Played By'].nunique())
                c3.metric("Avg Effort", f"{df['Effort'].mean():.1f}")
                c4.metric("Avg Rank (Global)", f"{df_full['Scenario Rank'].mean():.2f}")
                
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Dmg (Avg/Med)", f"{df['Damage'].mean():.1f} / {df['Damage'].median():.1f}")
                c6.metric("Heal (Avg/Med)", f"{df['Healing'].mean():.1f} / {df['Healing'].median():.1f}")
                c7.metric("Mitig. (Avg/Med)", f"{df['Mitigation'].mean():.1f} / {df['Mitigation'].median():.1f}")
                c8.metric("Avg Hand/Discard", f"{df['In Hand'].mean():.1f} / {df['Discard'].mean():.1f}")

            render_full_metrics(df_a, df_a_all, class_a)
            if compare_mode and not df_b.empty:
                st.divider()
                render_full_metrics(df_b, df_b_all, class_b)

        if st.session_state.show_charts:
            st.divider()
            c_rad, c_evol = st.columns([1, 2])
            with c_rad:
                st.write("**Role Signature**")
                radar_cols = ['Damage', 'Healing', 'Mitigation']
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
                if compare_mode and not df_b.empty:
                    fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
                fig_r.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_r, use_container_width=True)
            
            with c_evol:
                st.write("**Scientific Effort Modeling**")
                df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
                fig_m = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State', trendline="ols", template="plotly_dark")
                fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_m, use_container_width=True)

        if st.session_state.show_table:
            st.subheader("📋 Scenario Log")
            df_table = pd.concat([df_a, df_b]) if compare_mode else df_a
            st.dataframe(
                df_table.sort_values('Date', ascending=False),
                column_order=("Icon URL", "Date", "Class", "Scenario", "Rank String", "Effort", "Damage", "Healing", "Mitigation", "Result"),
                column_config={
                    "Icon URL": st.column_config.ImageColumn("Icon", width="small"),
                    "Effort": st.column_config.NumberColumn(format="%.1f")
                },
                use_container_width=True, hide_index=True
            )

with tab_road:
    st.header(f"Roadmap: {class_a}")
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty and 'Class' in df_campaigns.columns else 0
    st.metric("Campaign Sessions", camp_count)
    
    latest_state = df_a_all.sort_values('Date').iloc[-1]['Release State'] if not df_a_all.empty else "N/A"
    target = 5 if str(latest_state).lower() == "alpha" else 9
    st.info(f"Current State: **{latest_state}**. Data Coverage Target: Levels 1 to {target}")
    
    cov = pd.DataFrame([{"Level": l, "Tests": len(df_a_all[df_a_all['Class Level'] == l])} for l in range(1, 10)])
    fig_cov = px.bar(cov, x='Level', y='Tests', title="Data Coverage by Level", color_discrete_sequence=['#00d4ff'])
    fig_cov.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_cov, use_container_width=True)

with tab_settings:
    st.header("App Settings")
    st.session_state.show_metrics = st.checkbox("Show Performance Metrics", value=st.session_state.show_metrics)
    st.session_state.show_charts = st.checkbox("Show Analysis Charts", value=st.session_state.show_charts)
    st.session_state.show_table = st.checkbox("Show Data Table", value=st.session_state.show_table)
