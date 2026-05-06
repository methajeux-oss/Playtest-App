import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import requests
from email.utils import parsedate_to_datetime

# 1. CONFIGURATION DE LA PAGE
CCUG_LOGO_URL = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/CCUG.png"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/" # À adapter à votre repo
st.set_page_config(page_title="CCUG Playtest Portal", layout="wide", page_icon=CCUG_LOGO_URL)

# 2. DICTIONNAIRE DE TRADUCTION
T = {
    "sidebar_data": "📂 Configuration",
    "primary_class": "Classe principale",
    "comp_mode": "Mode Comparaison",
    "analysis_lvl": "Niveau d'analyse",
    "timeframe": "Période",
    "log": "Logs Scénarios",
    "roadmap": "Roadmap",
    "settings": "Paramètres"
}

# 3. MOTEUR DE DONNÉES (Chargement et calculs)
@st.cache_data(ttl=600)
def load_data():
    # Remplacez par votre URL Google Sheets CSV réelle
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT5uWIsV6M0v_I3B9S76o6Nlq_H8FvE0Wl5W7Y/pub?output=csv"
    df = pd.read_csv(SHEET_URL)
    
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # Nettoyage et calcul Effort
    for c in ['Damage', 'Healing', 'Mitigation', 'Class Level']:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    
    # Calcul du SID unique (Session ID) basé sur le lien Discord (le plus fiable)
    # Si pas de lien, on combine Date et Scénario
    df['sid'] = df['Test Result Link'].fillna(df['Date'].astype(str) + df['Scenario'])
    
    # Calcul du Rang dans la session
    df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
    df['Group Size'] = df.groupby('sid')['Class'].transform('count')
    df['Rank String'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
    
    return df

@st.cache_data(ttl=600)
def load_voters():
    try:
        return [str(v).strip().lower() for v in pd.read_csv(f"{GITHUB_RAW_BASE}voters.csv").iloc[:,0].tolist()]
    except: return []

@st.cache_data(ttl=600)
def load_card_links():
    try:
        return pd.read_csv(f"{GITHUB_RAW_BASE}class_cards.csv").set_index('Class').to_dict('index')
    except: return {}

df_raw = load_data()

# 4. SIDEBAR
st.sidebar.image(CCUG_LOGO_URL, width=100)
st.sidebar.header(T["sidebar_data"])

classes = ["🏠 Homepage"] + sorted([str(c) for c in df_raw['Class'].dropna().unique()])
class_a = st.sidebar.selectbox(T["primary_class"], classes)

compare_mode = st.sidebar.checkbox(T["comp_mode"]) if class_a != "🏠 Homepage" else False
class_b = None
if compare_mode:
    class_b = st.sidebar.selectbox("Seconde Classe", [c for c in classes if c != class_a and c != "🏠 Homepage"])

level_filter = st.sidebar.selectbox(T["analysis_lvl"], ["All Levels"] + list(range(1, 10))) if class_a != "🏠 Homepage" else "All Levels"

# 5. LOGIQUE D'AFFICHAGE PRINCIPALE
if class_a == "🏠 Homepage":
    # --- HOMEPAGE ---
    st.title("🏠 CCUG Playtest Portal")
    
    df_raw['Month_Year'] = df_raw['Date'].dt.strftime('%B %Y')
    month_options = df_raw.sort_values('Date', ascending=False)['Month_Year'].unique()
    selected_month = st.selectbox("📅 Analyser les tests de :", month_options)
    
    df_m = df_raw[df_raw['Month_Year'] == selected_month]
    
    st.header(f"🚀 Top 3 par Catégorie ({selected_month})")
    c1, c2, c3 = st.columns(3)
    for cat, col in [("Conceptual", c1), ("Alpha", c2), ("Beta", c3)]:
        with col:
            st.subheader(cat)
            top = df_m[df_m['Release State'].str.strip() == cat]['Class'].value_counts().head(3)
            if not top.empty:
                for i, (name, count) in enumerate(top.items()):
                    st.markdown(f"**{i+1}. {name}** ({count} tests)")
            else: st.info("Aucune donnée")

    st.divider()
    st.header("🏆 Top 3 Playtesters du mois")
    top_p = df_m['Played By'].value_counts().head(3)
    tc = st.columns(3)
    for i, (name, count) in enumerate(top_p.items()):
        tc[i].metric(f"Top {i+1}", name, f"{count} sessions")

else:
    # --- VUE PAR CLASSE ---
    def get_filtered(cls, lvl):
        mask = (df_raw['Class'] == cls)
        if lvl != "All Levels": mask &= (df_raw['Class Level'] == lvl)
        return df_raw[mask].copy()

    df_a = get_filtered(class_a, level_filter)
    df_a_all = get_filtered(class_a, "All Levels")

    tab_dash, tab_road, tab_testers, tab_assets, tab_settings = st.tabs([
        f"📊 {T['log']}", f"🎯 {T['roadmap']}", "👥 Testers", "🎨 Assets", f"⚙️ {T['settings']}"
    ])

    # --- TAB LOG (Résumé rapide) ---
    with tab_dash:
        st.header(f"Analyse de {class_a}")
        st.dataframe(df_a[['Date', 'Played By', 'Scenario', 'Rank String', 'Effort']], use_container_width=True)

    # --- TAB TESTERS ---
    with tab_testers:
        st.subheader("Statistiques des Testeurs")
        voters = load_voters()
        t_stats = df_a_all.groupby('Played By').agg({'Date': 'count', 'Class Level': lambda x: sorted(list(x.unique()))}).reset_index()
        t_stats['Voter'] = t_stats['Played By'].apply(lambda x: "⭐ Voter" if str(x).lower() in voters else "❌")
        st.table(t_stats.sort_values('Date', ascending=False))

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
                    st.markdown(f"**{state}s**")
                    cols = st.columns(4)
                    for i, m in enumerate(members):
                        bg = COLORS.get(state, "#eee")
                        tx = "white" if state == "Official" else "black"
                        cols[i%4].markdown(f'<div style="background:{bg}; color:{tx}; padding:5px; border-radius:5px; text-align:center; font-weight:bold; margin-bottom:5px;">{m}</div>', unsafe_allow_html=True)

    # --- TAB ASSETS ---
    with tab_assets:
        url_part = class_a.replace(" ", "%20")
        
        def show_mat(side, url):
            try:
                res = requests.head(url)
                if res.status_code == 200:
                    st.image(url, use_container_width=True)
                    date = parsedate_to_datetime(res.headers.get('Last-Modified')).strftime("%d/%m/%Y")
                    st.caption(f"📅 Mis à jour : {date}")
                else: st.info(f"Mat {side} non trouvé.")
            except: st.error("Erreur de chargement.")

        col1, col2 = st.columns(2)
        with col1: show_mat("Front", f"{GITHUB_RAW_BASE}assets/{url_part}%20front.png")
        with col2: show_mat("Back", f"{GITHUB_RAW_BASE}assets/{url_part}%20back.png")

        st.divider()
        st.subheader("🎴 Cartes")
        links = load_card_links()
        if class_a in links:
            if pd.notna(links[class_a].get('Level 1X')): st.image(links[class_a]['Level 1X'], caption="Level 1-X")
            if pd.notna(links[class_a].get('Level 2-9')): st.image(links[class_a]['Level 2-9'], caption="Level 2-9")
        
        st.divider()
        st.subheader("📦 Figurine 3D")
        stl_url = f"{GITHUB_RAW_BASE}assets/{url_part}.stl"
        st.components.v1.html(f"""
            <div id="v" style="width:100%; height:400px; background:#111;"></div>
            <script src="https://cdn.jsdelivr.net/npm/three@0.145.0/build/three.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.145.0/examples/js/loaders/STLLoader.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/three@0.145.0/examples/js/controls/OrbitControls.js"></script>
            <script>
                const scene = new THREE.Scene();
                const renderer = new THREE.WebGLRenderer({{antialias:true}});
                const container = document.getElementById('v');
                renderer.setSize(container.clientWidth, 400);
                container.appendChild(renderer.domElement);
                const camera = new THREE.PerspectiveCamera(45, container.clientWidth/400, 0.1, 1000);
                camera.position.set(0,0,100);
                const controls = new THREE.OrbitControls(camera, renderer.domElement);
                const light = new THREE.DirectionalLight(0xffffff, 1); light.position.set(1,1,1); scene.add(light);
                new THREE.STLLoader().load('{stl_url}', (geo) => {{
                    const mesh = new THREE.Mesh(geo, new THREE.MeshPhongMaterial({{color:0x00d4ff}}));
                    geo.computeBoundingBox(); geo.center(); scene.add(mesh);
                }}, undefined, (e) => {{ container.innerHTML = '<p style="color:white; text-align:center; padding-top:150px;">STL non trouvé</p>'; }});
                function anim() {{ requestAnimationFrame(anim); controls.update(); renderer.render(scene, camera); }}
                anim();
            </script>
        """, height=420)
