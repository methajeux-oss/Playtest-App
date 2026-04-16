import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Playtest App v2.0", layout="wide", page_icon="🛡️")

# 2. CONFIGURATION DES ICÔNES
# Utilisation du lien RAW pour GitHub
GITHUB_ICON_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/"

def get_icon_url(class_name):
    if pd.isna(class_name) or class_name == "":
        return ""
    clean_name = str(class_name).strip().replace(" ", "%20")
    return f"{GITHUB_ICON_BASE}{clean_name}.png"

# 3. SESSION STATE
if 'show_metrics' not in st.session_state: st.session_state.show_metrics = True
if 'show_charts' not in st.session_state: st.session_state.show_charts = True
if 'show_table' not in st.session_state: st.session_state.show_table = True

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.4rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    .class-header { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
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
            df = df.dropna(subset=['Class', 'Date'])
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            num_cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['Icon'] = df['Class'].apply(get_icon_url)
            
            # Scenario Rank Logic
            df['sid'] = df['Date'].dt.date.astype(str) + "_" + df['Scenario'].astype(str)
            df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('sid')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].astype(int).astype(str) + " / " + df['Group Size'].astype(int).astype(str)
            
        return df
    except Exception as e:
        st.error(f"Erreur de chargement: {e}")
        return pd.DataFrame()

# 5. SIDEBAR
st.sidebar.header("📂 Source des Données")
data_mode = st.sidebar.radio("Source:", ["Google Sheets (Live)", "Manual Upload"])

if data_mode == "Google Sheets (Live)":
    df_raw = load_data(BASE_URL + SCENARIO_GID)
    df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario CSV", type=['csv'])
    df_raw = load_data(file_scen) if file_scen else pd.DataFrame()
    df_campaigns = pd.DataFrame()

if df_raw.empty:
    st.info("En attente de données...")
    st.stop()

# --- FILTERS ---
# Correction de l'erreur TypeError : on enlève les valeurs nulles avant de trier
unique_classes = df_raw['Class'].dropna().unique()
classes = sorted([str(c) for c in unique_classes])

class_a = st.sidebar.selectbox("Classe Principale", classes)
st.sidebar.image(get_icon_url(class_a), width=100)

compare_mode = st.sidebar.checkbox("Mode Comparaison")
class_b = st.sidebar.selectbox("Classe Secondaire", [c for c in classes if c != class_a]) if compare_mode else None
if compare_mode: st.sidebar.image(get_icon_url(class_b), width=100)

level_filter = st.sidebar.selectbox("Niveau d'Analyse", range(1, 10))
date_range = st.sidebar.date_input("Période", [df_raw['Date'].min(), df_raw['Date'].max()])

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

# Outliers
with st.expander("⚠️ Gestion des Valeurs Aberrantes"):
    df_pool = pd.concat([df_a, df_b])
    if len(df_pool) >= 4:
        Q1, Q3 = df_pool['Effort'].quantile(0.25), df_pool['Effort'].quantile(0.75)
        IQR = Q3 - Q1
        out_mask = (df_pool['Effort'] < Q1 - 1.5*IQR) | (df_pool['Effort'] > Q3 + 1.5*IQR)
        outliers = df_pool[out_mask].index.tolist()
        to_drop = st.multiselect("Exclure de l'analyse :", outliers, format_func=lambda x: f"{df_pool.loc[x, 'Scenario']} ({df_pool.loc[x, 'Effort']})")
        df_a = df_a.drop([i for i in to_drop if i in df_a.index])
        if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])

# 7. TABS
tab_dash, tab_road, tab_settings = st.tabs(["📊 Dashboard", "🎯 Roadmap", "⚙️ Settings"])

with tab_dash:
    if df_a.empty:
        st.warning("Aucune donnée pour ces filtres.")
    else:
        if st.session_state.show_metrics:
            def render_full_metrics(df, df_full, name):
                col_img, col_txt = st.columns([1, 10])
                with col_img: st.image(get_icon_url(name), width=60)
                with col_txt: st.subheader(f"Statistiques : {name} (Niveau {level_filter})")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Playtests", len(df))
                c2.metric("Testeurs Uniques", df['Played By'].nunique())
                c3.metric("Effort Moyen", f"{df['Effort'].mean():.1f}")
                c4.metric("Rang Global", f"{df_full['Scenario Rank'].mean():.2f}")
                
                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Dégâts (Moy/Med)", f"{df['Damage'].mean():.1f} / {df['Damage'].median():.1f}")
                c6.metric("Soins (Moy/Med)", f"{df['Healing'].mean():.1f} / {df['Healing'].median():.1f}")
                c7.metric("Mitig. (Moy/Med)", f"{df['Mitigation'].mean():.1f} / {df['Mitigation'].median():.1f}")
                c8.metric("Cartes Main/Déf", f"{df['In Hand'].mean():.1f} / {df['Discard'].mean():.1f}")

            render_full_metrics(df_a, df_a_all, class_a)
            if compare_mode and not df_b.empty:
                st.divider()
                render_full_metrics(df_b, df_b_all, class_b)

        if st.session_state.show_charts:
            st.divider()
            c_rad, c_evol = st.columns([1, 2])
            with c_rad:
                radar_cols = ['Damage', 'Healing', 'Mitigation']
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
                if compare_mode and not df_b.empty:
                    fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
                fig_r.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark")
                st.plotly_chart(fig_r, use_container_width=True)
            
            with c_evol:
                df_plot = pd.concat([df_a, df_b]) if compare_mode else df_a
                fig_m = px.scatter(df_plot, x='Date', y='Effort', color='Class' if compare_mode else 'Release State', trendline="ols", template="plotly_dark", title="Modélisation Scientifique de l'Effort")
                st.plotly_chart(fig_m, use_container_width=True)

        if st.session_state.show_table:
            st.subheader("📋 Log des Scénarios")
            df_table = pd.concat([df_a, df_b]) if compare_mode else df_a
            st.dataframe(
                df_table.sort_values('Date', ascending=False),
                column_order=("Icon", "Date", "Class", "Scenario", "Rank String", "Effort", "Damage", "Healing", "Mitigation", "Result"),
                column_config={"Icon": st.column_config.ImageColumn("Icon")},
                use_container_width=True, hide_index=True
            )

with tab_road:
    st.header(f"Roadmap : {class_a}")
    camp_count = len(df_campaigns[df_campaigns['Class'] == class_a]) if not df_campaigns.empty and 'Class' in df_campaigns.columns else 0
    st.metric("Tests en Campagne", camp_count)
    
    latest_state = df_a_all.sort_values('Date').iloc[-1]['Release State'] if not df_a_all.empty else "N/A"
    target = 5 if str(latest_state).lower() == "alpha" else 9
    st.info(f"État actuel : **{latest_state}**. Cible de couverture : Niveaux 1 à {target}")
    
    cov = pd.DataFrame([{"Level": l, "Tests": len(df_a_all[df_a_all['Class Level'] == l])} for l in range(1, 10)])
    fig_cov = px.bar(cov, x='Level', y='Tests', title="Couverture des données par niveau", color_discrete_sequence=['#00d4ff'])
    st.plotly_chart(fig_cov, use_container_width=True)

with tab_settings:
    st.header("Réglages de l'Interface")
    st.session_state.show_metrics = st.checkbox("Afficher les Métriques", value=st.session_state.show_metrics)
    st.session_state.show_charts = st.checkbox("Afficher les Graphiques", value=st.session_state.show_charts)
    st.session_state.show_table = st.checkbox("Afficher le Tableau Log", value=st.session_state.show_table)
