import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V1.6", layout="wide", page_icon="⚖️")

# 2. STYLE
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.8rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    [data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #1e1e1e; border-radius: 4px 4px 0 0; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #00d4ff !important; color: #0e1117 !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. DATA CONNECTIONS
# GID 0 is usually the first sheet, GID for the second sheet needs to be specified
# Based on common GSheet structures, I've added a parameter for the second sheet
SCENARIO_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid=0"
CAMPAIGN_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid=1626241044"

@st.cache_data(ttl=300)
def load_data(source, is_scenario=True):
    try:
        df = pd.read_csv(source)
        if df.empty: return pd.DataFrame()
        
        if is_scenario:
            df = df.dropna(subset=['Class', 'Date'])
            df['Date'] = pd.to_datetime(df['Date'])
            numeric_cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
        return df
    except:
        return pd.DataFrame()

# 4. LOAD DATA
df_scenarios = load_data(SCENARIO_URL, is_scenario=True)
df_campaign = load_data(CAMPAIGN_URL, is_scenario=False)

# 5. SIDEBAR FILTERS
st.sidebar.header("⚙️ Global Settings")
if not df_scenarios.empty:
    class_list = sorted(df_scenarios['Class'].unique())
    selected_class = st.sidebar.selectbox("Select Class to Analyze", class_list)
    
    # Global metrics for the sidebar
    class_data = df_scenarios[df_scenarios['Class'] == selected_class]
    unique_players = class_data['Played By'].nunique()
    
    st.sidebar.metric("Unique Playtesters", unique_players)
    st.sidebar.write(f"👥 **Testers:** {', '.join(class_data['Played By'].unique())}")

# 6. MAIN INTERFACE TABS
tab_dashboard, tab_roadmap = st.tabs(["📈 Performance Analytics", "🎯 Testing Roadmap"])

with tab_dashboard:
    if df_scenarios.empty:
        st.info("Upload data or check connection.")
    else:
        # Re-using the logic from V1.5 for the dashboard
        level_selected = st.selectbox("Filter by Level", range(1, 10))
        df_filtered = df_scenarios[(df_scenarios['Class'] == selected_class) & (df_scenarios['Class Level'] == level_selected)]
        
        if df_filtered.empty:
            st.warning("No data for this level.")
        else:
            # Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Scenario Tests", len(df_filtered))
            c2.metric("Avg Effort", f"{df_filtered['Effort'].mean():.1f}")
            c3.metric("Hand Longevity (Avg)", f"{df_filtered['In Hand'].mean():.1f}")
            
            # Campaign Counter for this class
            camp_count = len(df_campaign[df_campaign['Class'] == selected_class]) if not df_campaign.empty else 0
            c4.metric("Campaign Tests", camp_count)
            
            # Charts
            col_radar, col_evol = st.columns([1, 2])
            with col_radar:
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=[df_filtered['Damage'].mean(), df_filtered['Healing'].mean(), df_filtered['Mitigation'].mean()],
                    theta=['Damage', 'Healing', 'Mitigation'], fill='toself', name=selected_class, line_color='#00d4ff'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark")
                st.plotly_chart(fig_radar, use_container_width=True)
            
            with col_evol:
                fig_evol = px.scatter(df_filtered, x='Date', y='Effort', color='Release State', trendline="lowess", template="plotly_dark")
                st.plotly_chart(fig_evol, use_container_width=True)

with tab_roadmap:
    st.header(f"Testing Recommendation: {selected_class}")
    
    # Determine current state based on latest entry
    latest_state = class_data.sort_values('Date').iloc[-1]['Release State'] if not class_data.empty else "Alpha"
    st.info(f"Current recorded state: **{latest_state}**")
    
    # Define Target Range
    target_range = range(1, 6) if latest_state == "Alpha" else range(1, 10)
    
    # Analyze Coverage
    coverage_data = []
    for lvl in target_range:
        count = len(class_data[class_data['Class Level'] == lvl])
        coverage_data.append({"Level": f"Level {lvl}", "Tests": count, "Value": count})
    
    df_cov = pd.DataFrame(coverage_data)
    
    # Visual recommendation
    fig_cov = px.bar(df_cov, x='Level', y='Tests', title=f"Test Coverage (Target: {latest_state})",
                     color='Tests', color_continuous_scale='RdYlGn')
    st.plotly_chart(fig_cov, use_container_width=True)
    
    # Logic Recommendation
    untested = [int(row['Level'].split()[1]) for index, row in df_cov.iterrows() if row['Tests'] == 0]
    
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        st.subheader("🚀 Priority Levels")
        if untested:
            st.error(f"URGENT: Test levels {untested} (0 data points)")
        else:
            st.success("All target levels have at least one test!")
            
    with col_rec2:
        st.subheader("👥 Tester Diversity")
        diversity_score = class_data['Played By'].nunique()
        if diversity_score < 3:
            st.warning(f"Only {diversity_score} testers. Try to get a new perspective!")
        else:
            st.success(f"Great variety! {diversity_score} different testers.")

    # Show Campaign Details
    st.divider()
    st.subheader("📜 Campaign Test History")
    if not df_campaign.empty:
        this_camp = df_campaign[df_campaign['Class'] == selected_class]
        if not this_camp.empty:
            st.dataframe(this_camp, use_container_width=True)
        else:
            st.write("No campaign tests recorded yet.")
