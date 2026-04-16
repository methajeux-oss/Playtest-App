import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V2.2", layout="wide", page_icon="🛡️")

# 2. CONFIGURATION DES ICÔNES (À ADAPTER)
# Remplacez par votre lien GitHub raw
GITHUB_ICON_BASE = "https://raw.githubusercontent.com/VOTRE_USER/VOTRE_REPO/main/icons/"

def get_icon_url(class_name):
    # On nettoie le nom pour l'URL (enlever espaces, etc.)
    clean_name = str(class_name).replace(" ", "%20")
    return f"{GITHUB_ICON_BASE}{clean_name}.png"

# 3. SESSION STATE & CSS (Simplifié pour la lecture)
if 'show_metrics' not in st.session_state: st.session_state.show_metrics = True
if 'show_charts' not in st.session_state: st.session_state.show_charts = True
if 'show_table' not in st.session_state: st.session_state.show_table = True

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.4rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    .class-header { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .class-icon { width: 50px; height: 50px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 4. DATA ENGINE
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
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            for c in ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            # Ajout de l'URL de l'icône pour le tableau
            df['Icon'] = df['Class'].apply(get_icon_url)
            # Rank Logic
            df['sid'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
        return df
    except: return pd.DataFrame()

# 5. SIDEBAR
st.sidebar.header("📂 Data Source")
data_mode = st.sidebar.radio("Source:", ["Google Sheets (Live)", "Manual Upload"])

if data_mode == "Google Sheets (Live)":
    df_raw = load_data(BASE_URL + SCENARIO_GID)
    df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario CSV", type=['csv'])
    df_raw = load_data(file_scen) if file_scen else pd.DataFrame()
    df_campaigns = pd.DataFrame()

if df_raw.empty: st.stop()

# --- FILTERS ---
classes = sorted(df_raw['Class'].unique())
class_a = st.sidebar.selectbox("Primary Class", classes)
# Affichage de l'icône sélectionnée dans la sidebar
st.sidebar.image(get_icon_url(class_a), width=80)

compare_mode = st.sidebar.checkbox("Comparison Mode")
class_b = st.sidebar.selectbox("Secondary Class", [c for c in classes if c != class_a]) if compare_mode else None
if compare_mode: st.sidebar.image(get_icon_url(class_b), width=80)

level_filter = st.sidebar.selectbox("Level Filter", range(1, 10))
date_range = st.sidebar.date_input("Period", [df_raw['Date'].min(), df_raw['Date'].max()])

# 6. PROCESSING
df_a = df_raw[(df_raw['Class'] == class_a) & (df_raw['Class Level'] == level_filter)]
df_a_all = df_raw[df_raw['Class'] == class_a]
df_b = df_raw[(df_raw['Class'] == class_b) & (df_raw['Class Level'] == level_filter)] if compare_mode else pd.DataFrame()
df_b_all = df_raw[df_raw['Class'] == class_b] if compare_mode else pd.DataFrame()

# 7. TABS
tab_dash, tab_road, tab_settings = st.tabs(["📊 Dashboard", "🎯 Roadmap", "⚙️ Settings"])

with tab_dash:
    if df_a.empty:
        st.warning("No data.")
    else:
        if st.session_state.show_metrics:
            def render_class_header(name):
                col1, col2 = st.columns([1, 10])
                with col1: st.image(get_icon_url(name), width=60)
                with col2: st.subheader(f"Results: {name} (Lvl {level_filter})")

            def render_stats(df, df_full):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Playtests", len(df))
                c2.metric("Testers", df['Played By'].nunique())
                c3.metric("Avg Effort", f"{df['Effort'].mean():.1f}")
                c4.metric("Avg Rank (Global)", f"{df_full['Scenario Rank'].mean():.2f}")
                
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Avg Dmg", f"{df['Damage'].mean():.1f}")
                c6.metric("Med Dmg", f"{df['Damage'].median():.1f}")
                c7.metric("Avg Heal", f"{df['Healing'].mean():.1f}")
                c8.metric("Med Heal", f"{df['Healing'].median():.1f}")

            render_class_header(class_a)
            render_stats(df_a, df_a_all)
            
            if compare_mode and not df_b.empty:
                st.divider()
                render_class_header(class_b)
                render_stats(df_b, df_b_all)

        if st.session_state.show_table:
            st.divider()
            st.subheader("📋 Scenario Log")
            df_table = pd.concat([df_a, df_b]) if compare_mode else df_a
            
            # Utilisation de column_config pour afficher l'image dans le tableau
            st.dataframe(
                df_table.sort_values('Date', ascending=False),
                column_order=("Icon", "Date", "Class", "Scenario", "Effort", "Damage", "Healing", "Mitigation", "Result"),
                column_config={
                    "Icon": st.column_config.ImageColumn("Icon", help="Class Icon"),
                    "Effort": st.column_config.NumberColumn(format="%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

with tab_settings:
    st.header("Settings")
    st.session_state.show_metrics = st.checkbox("Show Metrics", value=st.session_state.show_metrics)
    st.session_state.show_table = st.checkbox("Show Table", value=st.session_state.show_table)
