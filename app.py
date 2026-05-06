import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
from email.utils import parsedate_to_datetime

# 1. PAGE CONFIGURATION
CCUG_LOGO_URL = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/CCUG.png"
st.set_page_config(page_title="CCUG Playtest Portal", layout="wide", page_icon=CCUG_LOGO_URL)

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
        "modeling": "Effort Modeling",
        "log": "Scenario Log",
        "roadmap": "Testing Roadmap",
        "settings": "Settings",
        "theme_msg": "💡 Tip: Use **Dark Mode** for the best experience.",
        "priority_msg": "🎯 **Testing Priority:**",
        "coverage": "Data Coverage by Level",
        "campaign_sessions": "Campaign Sessions",
        "campaign_log": "📋 Campaign Tests Log",
        "outlier_title": "⚠️ Outlier Management",
        "outlier_desc": "Exclude from analysis:",
        "lang_select": "🌐 Change Language",
        "show_metrics": "Show Performance Metrics",
        "show_charts": "Show Analysis Charts",
        "show_table": "Show Data Table",
        "discord_btn": "Discord"
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
        "priority_msg": "🎯 **Priorité de Test :**",
        "coverage": "Couverture des données par niveau",
        "campaign_sessions": "Sessions en Campagne",
        "campaign_log": "📋 Log des Tests en Campagne",
        "outlier_title": "⚠️ Gestion des Valeurs Aberrantes",
        "outlier_desc": "Exclure de l'analyse :",
        "lang_select": "🌐 Changer la Langue",
        "show_metrics": "Afficher les Métriques de Performance",
        "show_charts": "Afficher les Graphiques d'Analyse",
        "show_table": "Afficher le Tableau des Données",
        "discord_btn": "Discord"
    }
}

if 'lang' not in st.session_state: st.session_state.lang = "Français"
T = LANGUAGES[st.session_state.lang]

# 3. ICON & CSS CONFIG
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/"
GITHUB_ICON_BASE = f"{GITHUB_RAW_BASE}icons/"

def get_icon_url(class_name):
    if pd.isna(class_name) or class_name == "" or class_name == "🏠 Homepage": return ""
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
        df = df.dropna(subset=['Class']) 
        if is_scenario:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            for c in ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['sid'] = df['Test Result Link'].fillna(df['Date'].astype(str) + df['Scenario'])
            df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('sid')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].fillna(0).astype(int).astype(str) + " / " + df['Group Size'].fillna(0).astype(int).astype(str)
        df['Icon URL'] = df['Class'].apply(get_icon_url)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def load_card_links():
    try:
        return pd.read_csv(f"{GITHUB_RAW_BASE}class_cards.csv").set_index('Class').to_dict('index')
    except: return {}

@st.cache_data(ttl=600)
def load_voters():
    try:
        return [str(v).strip().lower() for v in pd.read_csv(f"{GITHUB_RAW_BASE}voters.csv").iloc[:,0].tolist()]
    except: return []

# 5. SIDEBAR
st.sidebar.header(T["sidebar_data"])
df_raw = load_data(BASE_URL + SCENARIO_GID)
df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)

classes = ["🏠 Homepage"] + sorted([str(c) for c in df_raw['Class'].dropna().unique()])
class_a = st.sidebar.selectbox(T["primary_class"], classes)

# Affichage conditionnel des filtres si ce n'est pas la Homepage
if class_a != "🏠 Homepage":
    st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_a)}"></div>', unsafe_allow_html=True)
    compare_mode = st.sidebar.checkbox(T["comp_mode"])
    class_b = st.sidebar.selectbox(T["secondary_class"], [c for c in classes if c not in [class_a, "🏠 Homepage"]]) if compare_mode else None
    level_filter = st.sidebar.selectbox(T["analysis_lvl"], ["Tous"] + list(range(1, 10)))
    date_range = st.sidebar.date_input(T["timeframe"], [df_raw['Date'].min(), df_raw['Date'].max()])
else:
    compare_mode = False

# 6. PROCESSING (Seulement si une classe est sélectionnée)
if class_a != "🏠 Homepage":
    def get_filtered(cls, lvl=None):
        mask = (df_raw['Class'] == cls)
        if lvl and lvl != "Tous": mask &= (df_raw['Class Level'] == lvl)
        if len(date_range) == 2:
            mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
        return df_raw[mask].copy()

    df_a = get_filtered(class_a, level_filter)
    df_a_all = get_filtered(class_a)
    df_b = get_filtered(class_b, level_filter) if compare_mode else pd.DataFrame()
    df_b_all = get_filtered(class_b) if compare_mode else pd.DataFrame()

# 7. MAIN LAYOUT
if class_a == "🏠 Homepage":
    # --- CONTENU DE LA HOMEPAGE ---
    st.title("🏠 CCUG Playtest Portal")
    
    # Sélecteur de mois
    df_raw['Month_Year'] = df_raw['Date'].dt.strftime('%B %Y')
    month_options = df_raw.sort_values('Date', ascending=False)['Month_Year'].unique()
    selected_month = st.selectbox("📅 Choisir le mois à analyser", month_options)
    
    df_m = df_raw[df_raw['Month_Year'] == selected_month]
    
    # --- TOP CLASSES PAR CATÉGORIE ---
    st.header(f"🚀 Top 3 des classes les plus jouées ({selected_month})")
    c1, c2, c3 = st.columns(3)
    
    # Dictionnaire de couleurs pour les badges de la homepage
    CAT_COLORS = {"Conceptual": "#d3d3d3", "Alpha": "#ff4b4b", "Beta": "#90ee90"}
    
    for cat_name, col in [("Conceptual", c1), ("Alpha", c2), ("Beta", c3)]:
        with col:
            st.subheader(cat_name)
            top_cat = df_m[df_m['Release State'].str.strip().str.capitalize() == cat_name]['Class'].value_counts().head(3)
            if not top_cat.empty:
                for i, (name, count) in enumerate(top_cat.items()):
                    st.markdown(f"""
                        <div style="background:{CAT_COLORS[cat_name]}; color:black; padding:10px; border-radius:5px; margin-bottom:5px; border-left: 5px solid rgba(0,0,0,0.2);">
                            <strong>#{i+1} {name}</strong><br><small>{count} sessions</small>
                        </div>
                    """, unsafe_allow_html=True)
            else: st.info("Aucune donnée ce mois-ci")

    st.divider()

    # --- TOP TESTEURS ---
    st.header("🏆 Top 3 Testeurs du mois")
    top_testers = df_m['Played By'].value_counts().head(3)
    tc1, tc2, tc3 = st.columns(3)
    cols_testers = [tc1, tc2, tc3]
    
    for i, (name, count) in enumerate(top_testers.items()):
        with cols_testers[i]:
            st.metric(label=f"Position #{i+1}", value=name, delta=f"{count} sessions")

else:
    # --- VUE ANALYSE PAR CLASSE (ONGLETS) ---
    tab_dash, tab_road, tab_testers, tab_assets, tab_settings = st.tabs([
        f"📊 {T['log']}", f"🎯 {T['roadmap']}", "👥 Testers", "🎨 Assets", f"⚙️ {T['settings']}"
    ])

    with tab_dash:
        if df_a.empty: st.warning("Pas de données pour cette sélection.")
        else:
            # Métriques
            render_col1, render_col2 = st.columns(2)
            with render_col1:
                st.metric(T["playtests"], len(df_a))
                st.metric(T["avg_effort"], f"{df_a['Effort'].mean():.1f}")
            with render_col2:
                st.metric(T["unique_testers"], df_a['Played By'].nunique())
                st.metric(T["avg_rank"], f"{df_a_all['Scenario Rank'].mean():.2f}")
            
            st.divider()
            st.subheader(T["log"])
            st.dataframe(df_a.sort_values('Date', ascending=False), 
                         column_order=("Date", "Scenario", "Rank String", "Effort", "Result"), 
                         use_container_width=True, hide_index=True)

    with tab_testers:
        st.header(f"Statistiques des Testeurs ({class_a})")
        voters = load_voters()
        t_stats = df_a_all.groupby('Played By').agg({'Date': 'count', 'Class Level': lambda x: sorted(list(x.unique()))}).reset_index()
        t_stats['Voter'] = t_stats['Played By'].apply(lambda x: "⭐ Voter" if str(x).lower() in voters else "❌")
        st.dataframe(t_stats.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🤝 Classes rencontrées")
        sids = df_a_all['sid'].unique()
        df_comp = df_raw[(df_raw['sid'].isin(sids)) & (df_raw['Class'] != class_a)]
        if not df_comp.empty:
            comp_states = df_raw.groupby('Class')['Release State'].last().to_dict()
            ORDER = ["Official", "Released", "Beta", "Alpha", "Conceptual"]
            COLORS = {"Released": "#add8e6", "Beta": "#90ee90", "Alpha": "#ff4b4b", "Conceptual": "#d3d3d3", "Official": "#a333c8"}
            for state in ORDER:
                members = [c for c in sorted(df_comp['Class'].unique()) if comp_states.get(c) == state]
                if members:
                    st.markdown(f"#### {state}s")
                    cols = st.columns(4)
                    for i, m in enumerate(members):
                        bg = COLORS.get(state, "#eee")
                        tx = "white" if state == "Official" else "black"
                        cols[i%4].markdown(f'<div style="background:{bg}; color:{tx}; padding:8px; border-radius:5px; text-align:center; font-weight:bold; font-size:0.8em;">{m}</div>', unsafe_allow_html=True)

    with tab_assets:
        url_part = class_a.replace(" ", "%20")
        col_f, col_b = st.columns(2)
        
        def display_asset(url, label):
            try:
                resp = requests.head(url)
                if resp.status_code == 200:
                    st.image(url, use_container_width=True)
                    date_str = parsedate_to_datetime(resp.headers.get('Last-Modified')).strftime("%d/%m/%Y")
                    st.caption(f"📅 {label} mis à jour le : {date_str}")
                else: st.info(f"{label} non disponible.")
            except: pass

        with col_f: display_asset(f"{GITHUB_RAW_BASE}assets/{url_part}%20front.png", "Mat Front")
        with col_b: display_asset(f"{GITHUB_RAW_BASE}assets/{url_part}%20back.png", "Mat Back")

        st.divider()
        st.subheader("🎴 Cartes")
        cards = load_card_links()
        if class_a in cards:
            if pd.notna(cards[class_a].get('Level 1X')): st.image(cards[class_a]['Level 1X'], caption="Niveaux 1-X")
            if pd.notna(cards[class_a].get('Level 2-9')): st.image(cards[class_a]['Level 2-9'], caption="Niveaux 2-9")

    with tab_settings:
        st.header(T["settings"])
        st.selectbox(T["lang_select"], ["English", "Français"], key="lang")
        st.info(T["theme_msg"])
