import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V1.7", layout="wide", page_icon="⚖️")

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

# 4. HELPER FUNCTIONS
@st.cache_data(ttl=300)
def load_and_clean(source, is_scenario=True):
    try:
        df = pd.read_csv(source)
        if df.empty: return pd.DataFrame()
        if is_scenario:
            df = df.dropna(subset=['Class', 'Date'])
            df['Date'] = pd.to_datetime(df['Date'])
            cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
            for c in cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
        return df
    except:
        return pd.DataFrame()

def detect_outliers(df, col='Effort'):
    if len(df) < 4: return []
    Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
    IQR = Q3 - Q1
    return df[(df[col] < Q1 - 1.5*IQR) | (df[col] > Q3 + 1.5*IQR)].index.tolist()

# 5. SIDEBAR - DATA SOURCE & FILTERS
st.sidebar.header("📂 Data Management")
data_mode = st.sidebar.radio("Source:", ["Google Sheets (Live)", "Manual Upload (CSV)"])

df_scenarios = pd.DataFrame()
df_campaigns = pd.DataFrame()

if data_mode == "Google Sheets (Live)":
    df_scenarios = load_and_clean(BASE_URL + SCENARIO_GID)
    df_campaigns = load_and_clean(BASE_URL + CAMPAIGN_GID, is_scenario=False)
    st.sidebar.success("Connected to Live GSheet")
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario Tests", type=['csv'])
    file_camp = st.sidebar.file_uploader("Upload Campaign Tests (Optional)", type=['csv'])
    if file_scen: df_scenarios = load_and_clean(file_scen)
    if file_camp: df_campaigns = load_and_clean(file_camp, is_scenario=False)

if df_scenarios.empty:
    st.info("Please connect to a data source to begin.")
    st.stop()

# --- FILTERS ---
st.sidebar.divider()
classes = sorted(df_scenarios['Class'].unique())
class_a = st.sidebar.selectbox("Primary Class", classes)

compare_mode = st.sidebar.checkbox("Compare with another class")
class_b = st.sidebar.selectbox("Secondary Class", [c for c in classes if c != class_a]) if compare_mode else None

level_filter = st.sidebar.selectbox("Filter by Level", range(1, 10))
date_range = st.sidebar.date_input("Date Range", [df_scenarios['Date'].min(), df_scenarios['Date'].max()])

# User Diversity Metric in Sidebar
class_a_all = df_scenarios[df_scenarios['Class'] == class_a]
st.sidebar.metric("Unique Testers (Class A)", class_a_all['Played By'].nunique())
st.sidebar.write(f"👥 {', '.join(class_a_all['Played By'].unique())}")

# 6. DATA PREPARATION (Filtering & Outliers)
def get_filtered_df(cls):
    mask = (df_scenarios['Class'] == cls) & (df_scenarios['Class Level'] == level_filter)
    if len(date_range) == 2:
        mask &= (df_scenarios['Date'].dt.date >= date_range[0]) & (df_scenarios['Date'].dt.date <= date_range[1])
    return df_scenarios[mask].copy()

df_a = get_filtered_df(class_a)
df_b = get_filtered_df(class_b) if compare_mode else pd.DataFrame()

# Outlier Management Expander
with st.expander("⚠️ Outlier Management (Clean your data)"):
    df_total = pd.concat([df_a, df_b])
    outliers = detect_outliers(df_total)
    if outliers:
        to_drop = st.multiselect("Exclude these outliers:", outliers, 
                                format_func=lambda x: f"[{df_total.loc[x, 'Class']}] {df_total.loc[x, 'Date'].date()} - Scen: {df_total.loc[x, 'Scenario']} (Effort: {df_total.loc[x, 'Effort']})")
        df_a = df_a.drop([i for i in to_drop if i in df_a.index])
        if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])
    else:
        st.write("No statistical outliers detected.")

# 7. MAIN TABS
tab1, tab2 = st.tabs(["📊 Analytics Dashboard", "🎯 Testing Roadmap"])

with tab1:
    if df_a.empty:
        st.warning("No data found for Class A with these filters.")
    else:
        # --- METRICS ---
        def show_metrics(df, label):
            st.subheader(f"Results for {label}")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Tests", len(df))
            c2.metric("Effort (Avg)", f"{df['Effort'].mean():.1f}")
            c3.metric("Dmg (Avg)", f"{df['Damage'].mean():.1f}")
            c4.metric("Heal/Mit (Avg)", f"{(df['Healing'] + df['Mitigation']).mean():.1f}")
            c5.metric("Hand Med/Avg", f"{df['In Hand'].median():.1f} / {df['In Hand'].mean():.1f}")

        show_metrics(df_a, class_a)
        if compare_mode and not df_b.empty:
            st.divider()
            show_metrics(df_b, class_b)

        # --- CHARTS ---
        st.divider()
        col_rad, col_low = st.columns([1, 2])
        
        with col_rad:
            st.subheader("Role Signature")
            radar_cols = ['Damage', 'Healing', 'Mitigation']
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
            if compare_mode and not df_b.empty:
                fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark", showlegend=True)
            st.plotly_chart(fig_r, use_container_width=True)

        with col_low:
            st.subheader("Power Curve (Evolution)")
            df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
            fig_l = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State', trendline="lowess", template="plotly_dark")
            st.plotly_chart(fig_l, use_container_width=True)

with tab2:
    st.header(f"Roadmap for {class_a}")
    
    # 1. Campaign Counter
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty else 0
    st.metric("Total Campaign Tests", camp_count)
    
    # 2. Recommendation Logic
    latest_state = class_a_all.sort_values('Date').iloc[-1]['Release State'] if not class_a_all.empty else "Alpha"
    target_max = 5 if latest_state == "Alpha" else 9
    st.info(f"Class is currently in **{latest_state}** state. Target testing: Levels 1 to {target_max}.")
    
    # Coverage Chart
    cov_data = [{"Level": l, "Tests": len(class_a_all[class_a_all['Class Level'] == l])} for l in range(1, 10)]
    df_cov = pd.DataFrame(cov_data)
    df_cov['Priority'] = df_cov.apply(lambda x: "Target" if x['Level'] <= target_max else "Optional", axis=1)
    
    fig_cov = px.bar(df_cov, x='Level', y='Tests', color='Priority', 
                     color_discrete_map={"Target": "#00d4ff", "Optional": "#444444"},
                     title="Test Distribution by Level")
    st.plotly_chart(fig_cov, use_container_width=True)
    
    # Recommendations
    missing = [r['Level'] for i, r in df_cov.iterrows() if r['Tests'] == 0 and r['Level'] <= target_max]
    if missing:
        st.error(f"🚨 **Next Steps:** Please test levels {missing} to validate the {latest_state} version.")
    else:
        st.success("✅ Target coverage achieved! Ready for state transition or focus on outliers.")

    # 3. Campaign Data Log
    if not df_campaigns.empty:
        st.divider()
        st.subheader("Campaign History")
        st.dataframe(df_campaigns[df_campaigns['Class'] == class_a], use_container_width=True)
