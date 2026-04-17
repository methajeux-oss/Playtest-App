import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Frosthaven Class Lab V2.6", layout="wide", page_icon="🛡️")

# 2. TRANSLATION DICTIONARY
LANGUAGES = {
    "English": {
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
        "theme_msg": "💡 Tip: Use **Dark Mode** for the best experience (Settings > Theme).",
        "conceptual_msg": "🧪 **Conceptual Class:** Focus on Level 1 to validate core mechanics.",
        "coverage": "Data Coverage by Level",
        "campaign_sessions": "Campaign Sessions",
        "outlier_title": "⚠️ Outlier Management",
        "outlier_desc": "Exclude from analysis:",
        "lang_select": "🌐 Change Language"
    },
    "Français": {
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
        "theme_msg": "💡 Conseil : Utilisez le **Mode Sombre** pour une meilleure expérience.",
        "conceptual_msg": "🧪 **Classe Conceptuelle :** Concentrez les tests sur le Niveau 1.",
        "coverage": "Couverture des données par niveau",
        "campaign_sessions": "Sessions en Campagne",
        "outlier_title": "⚠️ Gestion des Valeurs Aberrantes",
        "outlier_desc": "Exclure de l'analyse :",
        "lang_select": "🌐 Changer la Langue"
    }
}

# Initialisation de la langue
if 'lang' not in st.session_state: st.session_state.lang = "English"
T = LANGUAGES[st.session_state.lang]

# 3. ICON & CSS CONFIG
GITHUB_ICON_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/"

def get_icon_url(class_name):
    if pd.isna(class_name) or class_name == "": return ""
    clean_name = str(class_name).strip().replace(" ", "%20")
    return f"{GITHUB_ICON_BASE}{clean_name}.png"

st.markdown(f"""
    <style>
    [data-testid="stMetricValue"] {{ color: #00d4ff; font-size: 1.2rem; }}
    .icon-container {{
        width: 70px; height: 70px; display: flex; align-items: center; justify-content: center;
        overflow: hidden; border-radius: 8px; background-color: rgba(127, 127, 127, 0.1);
    }}
    .icon-container img {{ width: 100%; height: 100%; object-fit: contain; }}
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

# 5. SIDEBAR
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
if compare_mode: st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_b)}"></div>', unsafe_allow_html=True)

level_filter = st.sidebar.selectbox(T["analysis_lvl"], range(1, 10))
date_range = st.sidebar.date_input(T["timeframe"], [df_raw['Date'].min(), df_raw['Date'].max()])

# 6. PROCESSING
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

# 7. TABS
tab_dash, tab_road, tab_settings = st.tabs([f"📊 {T['log']}", f"🎯 {T['roadmap']}", f"⚙️ {T['settings']}"])

with tab_dash:
    if df_a.empty:
        st.warning("No data found for the selected level.")
    else:
        # CONCEPTUAL ALERT
        release_state = df_a_all.sort_values('Date').iloc[-1]['Release State'] if not df_a_all.empty else ""
        if str(release_state).lower() == "conceptual":
            st.warning(T["conceptual_msg"])

        # OUTLIER MANAGEMENT (RESTORED)
        with st.expander(T["outlier_title"]):
            df_pool = pd.concat([df_a, df_b])
            if len(df_pool) >= 4:
                Q1, Q3 = df_pool['Effort'].quantile(0.25), df_pool['Effort'].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df_pool[(df_pool['Effort'] < Q1 - 1.5*IQR) | (df_pool['Effort'] > Q3 + 1.5*IQR)].index.tolist()
                to_drop = st.multiselect(T["outlier_desc"], outliers, format_func=lambda x: f"{df_pool.loc[x, 'Scenario']} (Effort: {df_pool.loc[x, 'Effort']})")
                df_a = df_a.drop([i for i in to_drop if i in df_a.index])
                if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])

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

        # CHARTS (RESTORED)
        st.divider()
        c_rad, c_evol = st.columns([1, 2])
        with c_rad:
            st.write(f"**{T['role_sig']}**")
            radar_cols = ['Damage', 'Healing', 'Mitigation']
            fig_r = go.Figure()
            fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
            if compare_mode and not df_b.empty:
                fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
            fig_r.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_r, use_container_width=True)
        
        with c_evol:
            st.write(f"**{T['modeling']}**")
            df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
            fig_m = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State', trendline="ols", template="plotly_dark")
            fig_m.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_m, use_container_width=True)

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
    
    # NEW LANGUAGE SELECTOR POSITION
    st.selectbox(T["lang_select"], ["English", "Français"], key="lang")
    
    st.divider()
    st.info(T["theme_msg"])
