import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. CONFIGURATION DE LA PAGE
st.set_page_config(page_title="Frosthaven Class Lab V1.4", layout="wide", page_icon="⚖️")

# 2. STYLE DARK MODE ET METRICS
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-size: 1.8rem; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTable { background-color: #1e1e1e; }
    [data-testid="stExpander"] { background-color: #161b22; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 3. FONCTIONS DE CALCUL ET NETTOYAGE
def load_data(file):
    df = pd.read_csv(file)
    df = df.dropna(subset=['Class', 'Date'])
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Conversion numérique pour toutes les colonnes de données
    numeric_cols = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard', 'Effort']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Recalcul de la formule d'effort par sécurité
    # Effort = damage + (healing + mitigation) * 0.75
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    return df

def detect_outliers(df, column):
    """Algorithme Interquartile Range (IQR) pour détecter les anomalies statistiques."""
    if df.empty or len(df) < 4: return []
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] < lower_bound) | (df[column] > upper_bound)].index.tolist()

# 4. TITRE
st.title("🛡️ Frosthaven Class Lab : Analyseur Intégral")

uploaded_file = st.sidebar.file_uploader("Charger 'Scenario Tests.csv'", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- SIDEBAR : FILTRES ---
    st.sidebar.header("⚙️ Configuration")
    
    # Sélection des classes
    classe_a = st.sidebar.selectbox("Classe Principale", sorted(df_raw['Class'].unique()))
    
    comparaison_on = st.sidebar.checkbox("Activer le mode comparaison")
    classe_b = None
    if comparaison_on:
        classe_b = st.sidebar.selectbox("Classe à comparer", [c for c in sorted(df_raw['Class'].unique()) if c != classe_a])

    # Niveau Unique
    level_selected = st.sidebar.selectbox("Niveau des tests", range(1, 10))

    # RESTAURATION DU CALENDRIER
    min_date = df_raw['Date'].min().to_pydatetime()
    max_date = df_raw['Date'].max().to_pydatetime()
    date_range = st.sidebar.date_input("Période d'analyse", [min_date, max_date])

    # --- FILTRAGE DES DONNÉES ---
    def filter_class_data(cls, lvl, dates):
        mask = (df_raw['Class'] == cls) & (df_raw['Class Level'] == lvl)
        if len(dates) == 2:
            mask &= (df_raw['Date'].dt.date >= dates[0]) & (df_raw['Date'].dt.date <= dates[1])
        return df_raw[mask].copy()

    df_a = filter_class_data(classe_a, level_selected, date_range)
    
    if df_a.empty:
        st.warning(f"Aucune donnée pour {classe_a} au niveau {level_selected} sur cette période.")
    else:
        # --- GESTION DES VALEURS ABERRANTES (OUTLIERS) ---
        # On combine les données si comparaison pour détecter les outliers globaux
        df_to_check = df_a.copy()
        if comparaison_on and classe_b:
            df_b_temp = filter_class_data(classe_b, level_selected, date_range)
            df_to_check = pd.concat([df_a, df_b_temp])

        outlier_indices = detect_outliers(df_to_check, 'Effort')

        with st.expander("⚠️ Gestion des résultats aberrants (Outliers)"):
            if outlier_indices:
                st.write("L'algorithme a détecté des tests dont l'Effort est statistiquement suspect.")
                to_exclude = st.multiselect(
                    "Cochez les lignes à ignorer pour les statistiques et graphiques :",
                    outlier_indices,
                    format_func=lambda x: f"[{df_to_check.loc[x, 'Class']}] {df_to_check.loc[x, 'Date'].date()} - Scénario: {df_to_check.loc[x, 'Scenario']} (Effort: {df_to_check.loc[x, 'Effort']})"
                )
                if to_exclude:
                    df_a = df_a.drop([i for i in to_exclude if i in df_a.index])
                    st.info(f"Analyse mise à jour. Données exclues : {len(to_exclude)}")
            else:
                st.success("Aucune anomalie statistique détectée sur l'Effort.")

        # Re-préparation de la classe B après exclusion potentielle
        df_b = pd.DataFrame()
        if comparaison_on and classe_b:
            df_b = filter_class_data(classe_b, level_selected, date_range)
            if outlier_indices:
                df_b = df_b.drop([i for i in to_exclude if i in df_b.index])

        # --- AFFICHAGE DES MÉTRIQUES (2 CATÉGORIES) ---
        def display_class_metrics(df_target, name):
            st.subheader(f"📊 Statistiques : {name}")
            # Catégorie 1 : Performance Combat
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Playtests", len(df_target))
            c2.metric("Dégâts (Avg)", f"{df_target['Damage'].mean():.1f}")
            c3.metric("Soin (Avg)", f"{df_target['Healing'].mean():.1f}")
            c4.metric("Mitigation (Avg)", f"{df_target['Mitigation'].mean():.1f}")
            c5.metric("EFFORT CIBLE", f"{df_target['Effort'].mean():.1f}")
            
            # Catégorie 2 : Gestion de main
            st.markdown(f"*Gestion des cartes pour {name}*")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Main (Moy)", f"{df_target['In Hand'].mean():.1f}")
            m2.metric("Main (Méd)", f"{df_target['In Hand'].median():.1f}")
            m3.metric("Défausse (Moy)", f"{df_target['Discard'].mean():.1f}")
            m4.metric("Défausse (Méd)", f"{df_target['Discard'].median():.1f}")

        display_class_metrics(df_a, classe_a)
        if comparaison_on and not df_b.empty:
            st.divider()
            display_class_metrics(df_b, classe_b)

        st.divider()

        # --- GRAPHIQUES : ARAIGNÉE ET ÉVOLUTION ---
        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.subheader("🎯 Radar de Rôle")
            categories = ['Damage', 'Healing', 'Mitigation']
            fig_radar = go.Figure()
            
            # Trace Classe A
            fig_radar.add_trace(go.Scatterpolar(
                r=[df_a['Damage'].mean(), df_a['Healing'].mean(), df_a['Mitigation'].mean()],
                theta=categories, fill='toself', name=classe_a, line_color='#00d4ff'
            ))
            
            # Trace Classe B
            if comparaison_on and not df_b.empty:
                fig_radar.add_trace(go.Scatterpolar(
                    r=[df_b['Damage'].mean(), df_b['Healing'].mean(), df_b['Mitigation'].mean()],
                    theta=categories, fill='toself', name=classe_b, line_color='#ff4b4b'
                ))
            
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, gridcolor="#444")),
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=True
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_right:
            st.subheader("📈 Évolution de l'Effort par Date")
            df_plot = df_a.copy()
            if comparaison_on and not df_b.empty:
                df_plot = pd.concat([df_a, df_b])
            
            # Axe temporel uniquement par Date
            fig_evol = px.scatter(
                df_plot, x='Date', y='Effort', color='Class' if comparaison_on else 'Release State',
                trendline="lowess",
                title="Modélisation de la courbe de puissance",
                template="plotly_dark",
                hover_data=['Scenario', 'Played By', 'Damage', 'Result']
            )
            st.plotly_chart(fig_evol, use_container_width=True)

        # --- DÉTAILS DES SCÉNARIOS ---
        st.subheader("📋 Détail des scénarios")
        cols_to_show = ['Date', 'Class', 'Release State', 'Scenario', 'Damage', 'Healing', 'Mitigation', 'Effort', 'In Hand', 'Discard', 'Result']
        st.dataframe(df_plot[cols_to_show].sort_values('Date', ascending=False), use_container_width=True)

else:
    st.info("Veuillez charger le fichier CSV pour activer l'outil d'analyse.")
