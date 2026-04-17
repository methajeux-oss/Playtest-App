import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V2.5", layout="wide", page_icon="🛡️")

# 2. TRANSLATION DICTIONARY
LANGUAGES = {
    "English": {
        "lang_code": "en",
        "sidebar_data": "📂 Data Connection",
        "source": "Source:",
        "primary_class": "Primary Class",
        "secondary_class": "Secondary Class",
        "comp_mode": "Comparison Mode",
        "analysis_lvl": "Analysis Level",
        "timeframe": "Timeframe",
        "playtests": "Playtests",
        "unique_testers": "Unique Testers",
        "avg_effort": "Avg Effort",
        "avg_rank": "Avg Rank (Global)",
        "dmg": "Damage",
        "heal": "Healing",
        "mitig": "Mitigation",
        "hand_mgmt": "Avg Hand/Discard",
        "role_sig": "Role Signature",
        "modeling": "Scientific Effort Modeling",
        "log": "Scenario Log",
        "roadmap": "Testing Roadmap",
        "settings": "Settings",
        "theme_msg": "💡 Tip: This app is optimized for **Dark Mode** (Settings > Theme).",
        "conceptual_msg": "🧪 **Conceptual Class:** Focus should be on Level 1 to validate core mechanics first.",
        "coverage": "Data Coverage by Level",
        "campaign_sessions": "Campaign Sessions"
    },
    "Français": {
        "lang_code": "fr",
        "sidebar_data": "📂 Connexion des Données",
        "source": "Source :",
        "primary_class": "Classe Principale",
        "secondary_class": "Classe Secondaire",
        "comp_mode": "Mode Comparaison",
        "analysis_lvl": "Niveau d'Analyse",
        "timeframe": "Période",
        "playtests": "Playtests",
        "unique_testers": "Testeurs Uniques",
        "avg_effort": "Effort Moyen",
        "avg_rank": "Rang Global",
        "dmg": "Dégâts",
        "heal": "Soin",
        "mitig": "Mitigation",
        "hand_mgmt": "Main/Défausse Moy.",
        "role_sig": "Signature du Rôle",
        "modeling": "Modélisation de l'Effort",
        "log": "Log des Scénarios",
        "roadmap": "Roadmap de Tests",
        "settings": "Paramètres",
        "theme_msg": "💡 Conseil : Le site est optimisé pour le **Mode Sombre**.",
        "conceptual_msg": "🧪 **Classe Conceptuelle :** Les tests doivent se concentrer sur le Niveau 1 pour valider le fonctionnement.",
        "coverage": "Couverture des données par niveau",
        "campaign_sessions": "Sessions en Campagne"
    }
}

# 3. LANGUAGE SELECTION
if 'lang' not in st.session_state: st.session_state.lang = "English"
st.sidebar.selectbox("🌐 Language / Langue", ["English", "Français"], key="lang")
T = LANGUAGES[st.session_state.lang]

# 4. ICON & CSS CONFIG
GITHUB_ICON_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/"

def get_icon_url(class_name):
    if pd.isna(class_name) or class_name == "": return ""
    clean_name = str(class_name).strip().replace(" ", "%20")
    return f"{GITHUB_ICON_BASE}{clean_name}.png"

st.markdown(f"""
    <style>
    [data-testid="stMetricValue"] {{ color: #00d4ff; font-size: 1.4rem; }}
    .icon-container {{
        width: 80px; height: 80px; display: flex; align-items: center; justify-content: center;
        overflow: hidden; border-radius: 8px; background-color: rgba(127, 127, 127, 0.1);
    }}
    .icon-container img {{ width: 100%; height: 100%; object-fit: contain; }}
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
        if is_scenario:
            df = df.dropna(subset=['Class', 'Date'])
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            for c in ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['Icon URL'] = df['Class'].apply(get_icon_url)
            df['sid'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('sid')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
        return df
    except: return pd.DataFrame()

# 6. SIDEBAR
st.sidebar.info(T["theme_msg"])
st.sidebar.header(T["sidebar_data"])
data_mode = st.sidebar.radio(T["source"], ["Google Sheets", "Manual Upload"])

if data_mode == "Google Sheets":
    df_raw = load_data(BASE_URL + SCENARIO_GID)
    df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario CSV", type=['csv'])
    df_raw = load_data(file_scen) if file_scen else pd.DataFrame()
    df_campaigns = pd.DataFrame()

if df_raw.empty: st.stop()

# --- FILTERS ---
classes = sorted([str(c) for c in df_raw['Class'].dropna().unique()])
class_a = st.sidebar.selectbox(T["primary_class"], classes)
st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_a)}"></div>', unsafe_allow_html=True)

compare_mode = st.sidebar.checkbox(T["comp_mode"])
class_b = st.sidebar.selectbox(T["secondary_class"], [c for c in classes if c != class_a]) if compare_mode else None

level_filter = st.sidebar.selectbox(T["analysis_lvl"], range(1, 10))
date_range = st.sidebar.date_input(T["timeframe"], [df_raw['Date'].min(), df_raw['Date'].max()])

# 7. PROCESSING
df_a = df_raw[(df_raw['Class'] == class_a) & (df_raw['Class Level'] == level_filter)]
df_a_all = df_raw[df_raw['Class'] == class_a]
df_b = df_raw[(df_raw['Class'] == class_b) & (df_raw['Class Level'] == level_filter)] if compare_mode else pd.DataFrame()
df_b_all = df_raw[df_raw['Class'] == class_b] if compare_mode else pd.DataFrame()

# 8. TABS
tab_dash, tab_road, tab_settings = st.tabs([f"📊 {T['log']}", f"🎯 {T['roadmap']}", f"⚙️ {T['settings']}"])

with tab_dash:
    if df_a.empty:
        st.warning("No data found.")
    else:
        # CONCEPTUAL ALERT
        release_state = df_a_all.sort_values('Date').iloc[-1]['Release State'] if not df_a_all.empty else ""
        if str(release_state).lower() == "conceptual":
            st.warning(T["conceptual_msg"])

        def render_stats(df, df_full, name):
            col_img, col_txt = st.columns([1, 12])
            with col_img: st.markdown(f'<div class="icon-container"><img src="{get_icon_url(name)}"></div>', unsafe_allow_html=True)
            with col_txt: st.subheader(f"{name} - Level {level_filter}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(T["playtests"], len(df))
            c2.metric(T["unique_testers"], df['Played By'].nunique())
            c3.metric(T["avg_effort"], f"{df['Effort'].mean():.1f}")
            c4.metric(T["avg_rank"], f"{df_full['Scenario Rank'].mean():.2f}")
            
            c5, c6, c7, c8 = st.columns(4)
            c5.metric(f"{T['dmg']} (Avg/Med)", f"{df['Damage'].mean():.1f} / {df['Damage'].median():.1f}")
            c6.metric(f"{T['heal']} (Avg/Med)", f"{df['Healing'].mean():.1f} / {df['Healing'].median():.1f}")
            c7.metric(f"{T['mitig']} (Avg/Med)", f"{df['Mitigation'].mean():.1f} / {df['Mitigation'].median():.1f}")
            c8.metric(T["hand_mgmt"], f"{df['In Hand'].mean():.1f} / {df['Discard'].mean():.1f}")

        render_stats(df_a, df_a_all, class_a)
        if compare_mode and not df_b.empty:
            st.divider()
            render_stats(df_b, df_b_all, class_b)

        st.divider()
        st.subheader(f"📋 {T['log']}")
        df_table = pd.concat([df_a, df_b]) if compare_mode else df_a
        st.dataframe(
            df_table.sort_values('Date', ascending=False),
            column_order=("Icon URL", "Date", "Class", "Scenario", "Rank String", "Effort", "Damage", "Healing", "Mitigation", "Result"),
            column_config={"Icon URL": st.column_config.ImageColumn("Icon", width="small")},
            use_container_width=True, hide_index=True
        )

with tab_road:
    st.header(f"{T['roadmap']}: {class_a}")
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty and 'Class' in df_campaigns.columns else 0
    st.metric(T["campaign_sessions"], camp_count)
    
    cov = pd.DataFrame([{"Level": l, "Tests": len(df_a_all[df_a_all['Class Level'] == l])} for l in range(1, 10)])
    fig_cov = px.bar(cov, x='Level', y='Tests', title=T["coverage"], color_discrete_sequence=['#00d4ff'])
    fig_cov.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_cov, use_container_width=True)

with tab_settings:
    st.header(T["settings"])
    st.info(T["theme_msg"])
