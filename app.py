import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURATION (Utilisation du logo CCUG)
CCUG_LOGO_URL = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/CCUG.png"
st.set_page_config(page_title="CCUG Playtest App", layout="wide", page_icon=CCUG_LOGO_URL)

# 2. DICTIONNAIRE DE TRADUCTION
LANGUAGES = {
    "English": {
        "sidebar_data": "📂 Data Connection", "source": "Source:", "primary_class": "Primary Class",
        "secondary_class": "Secondary Class", "comp_mode": "Comparison Mode", "analysis_lvl": "Level",
        "timeframe": "Timeframe", "playtests": "Playtests", "avg_effort": "Avg Effort",
        "avg_rank": "Avg Rank", "dmg": "Dmg", "heal": "Heal", "mitig": "Mitig",
        "log": "Scenario Log", "roadmap": "Roadmap", "settings": "Settings",
        "discord_btn": "Discord", "err_load": "❌ Connection failed. Check your Sheet link or permissions.",
        "campaign_log": "📋 Campaign Tests Log"
    },
    "Français": {
        "sidebar_data": "📂 Connexion des Données", "source": "Source :", "primary_class": "Classe Principale",
        "secondary_class": "Classe Secondaire", "comp_mode": "Mode Comparaison", "analysis_lvl": "Niveau",
        "timeframe": "Période", "playtests": "Playtests", "avg_effort": "Effort Moyen",
        "avg_rank": "Rang Global", "dmg": "Dégâts", "heal": "Soin", "mitig": "Mitigation",
        "log": "Log Scénarios", "roadmap": "Roadmap", "settings": "Paramètres",
        "discord_btn": "Discord", "err_load": "❌ Échec de connexion. Vérifiez le lien Google Sheet.",
        "campaign_log": "📋 Log des Tests en Campagne"
    }
}

if 'lang' not in st.session_state: st.session_state.lang = "Français"
T = LANGUAGES[st.session_state.lang]

# 3. MOTEUR DE DONNÉES
SCENARIO_GID = "0"
CAMPAIGN_GID = "718802502" 
BASE_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid="
GITHUB_RAW = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/"

def get_icon_url(name):
    if pd.isna(name): return ""
    return f"{GITHUB_RAW}icons/{str(name).strip().replace(' ', '%20')}.png"

@st.cache_data(ttl=300)
def load_data(url, is_scenario=True):
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        if is_scenario and not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # Calculs de sécurité pour l'Effort (basés sur vos colonnes CSV) 
            cols_to_fix = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
            for c in cols_to_fix:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['Icon URL'] = df['Class'].apply(get_icon_url)
        elif not is_scenario and not df.empty:
            df['Icon URL'] = df['Class'].apply(get_icon_url)
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_links():
    try:
        df = pd.read_csv(f"{GITHUB_RAW}class_links.csv", sep=';')
        df.columns = [c.strip() for c in df.columns]
        return df
    except: return pd.DataFrame()

# Chargement
df_raw = load_data(BASE_URL + SCENARIO_GID)
df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
df_links = load_links()

# 4. GESTION DES ERREURS DE CONNEXION
if df_raw.empty:
    st.error(T["err_load"])
    st.info("💡 Vérifiez que le Google Sheet est partagé en 'Tous les utilisateurs disposant du lien'.")
    st.stop()

# 5. FILTRES SIDEBAR
st.sidebar.header(T["sidebar_data"])
classes = sorted(df_raw['Class'].unique())
class_a = st.sidebar.selectbox(T["primary_class"], classes)
compare_mode = st.sidebar.checkbox(T["comp_mode"])
class_b = st.sidebar.selectbox(T["secondary_class"], [c for c in classes if c != class_a]) if compare_mode else None
level_filter = st.sidebar.selectbox(T["analysis_lvl"], range(1, 10))

# 6. LAYOUT (Onglets à gauche, Discord à droite)
col_tabs, col_disc = st.columns([0.85, 0.15])

with col_tabs:
    tab_dash, tab_road, tab_settings = st.tabs([f"📊 {T['log']}", f"🎯 {T['roadmap']}", f"⚙️ {T['settings']}"])

with col_disc:
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    if not df_links.empty:
        link = df_links[df_links['Class'].str.strip() == class_a].Discord.values
        if len(link) > 0: st.link_button(f"💬 {T['discord_btn']}", link[0], use_container_width=True)

# 7. CONTENU DES ONGLETS
with tab_dash:
    # (Votre logique habituelle de dashboard ici...)
    st.write(f"Displaying {class_a}")

with tab_road:
    st.header(T["roadmap"])
    df_camp_total = df_campaigns[df_campaigns['Class'].isin([class_a, class_b] if compare_mode else [class_a])]
    
    if not df_camp_total.empty:
        st.subheader(T["campaign_log"])
        
        # --- FIX: LOGIQUE DE COLONNES DYNAMIQUES ---
        # On prend toutes les colonnes existantes pour ne rien perdre
        cols = list(df_camp_total.columns)
        if "Icon URL" in cols:
            cols.remove("Icon URL")
            order = ["Icon URL"] + cols # Icône toujours en premier
        else: order = cols

        st.dataframe(
            df_camp_total, 
            column_order=order,
            column_config={"Icon URL": st.column_config.ImageColumn("Icon", width="small")},
            use_container_width=True, hide_index=True
        )

with tab_settings:
    new_lang = st.selectbox("Language", ["English", "Français"], index=1 if st.session_state.lang == "Français" else 0)
    if new_lang != st.session_state.lang:
        st.session_state.lang = new_lang
        st.rerun()
