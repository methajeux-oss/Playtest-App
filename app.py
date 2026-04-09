import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuration
st.set_page_config(page_title="Frosthaven Class Lab", layout="wide")

# Style Dark Mode forcé pour les métriques
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; }
    .stApp { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

def load_data(file):
    df = pd.read_csv(file)
    df = df.dropna(subset=['Class', 'Date'])
    df['Date'] = pd.to_datetime(df['Date'])
    for col in ['Damage', 'Healing', 'Mitigation', 'Class Level']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    # Formule d'Effort
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    return df

def detect_outliers(df, column):
    """Algorithme Interquartile Range (IQR) pour détecter les anomalies."""
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] < lower_bound) | (df[column] > upper_bound)].index.tolist()

st.title("🛡️ Frosthaven Class Lab : Analyse Mono-Classe")

uploaded_file = st.sidebar.file_uploader("Fichier CSV", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- FILTRES SIDEBAR ---
    st.sidebar.header("🎯 Filtres")
    classe = st.sidebar.selectbox("Classe", sorted(df_raw['Class'].unique()))
    level = st.sidebar.selectbox("Niveau Unique", range(1, 10))
    
    # Retour du Calendrier
    min_d, max_d = df_raw['Date'].min(), df_raw['Date'].max()
    date_range = st.sidebar.date_input("Période d'analyse", [min_d, max_d])
    
    x_axis_mode = st.sidebar.radio("Axe temporel :", ["Date", "Release State"])

    # --- FILTRAGE INITIAL ---
    mask = (df_raw['Class'] == classe) & (df_raw['Class Level'] == level)
    if len(date_range) == 2:
        mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
    
    df_filtered = df_raw[mask].copy()

    if df_filtered.empty:
        st.warning("Aucune donnée pour cette sélection.")
    else:
        # --- DÉTECTION D'OUTLIERS ---
        outlier_indices = detect_outliers(df_filtered, 'Effort')
        
        # --- INTERFACE D'EXCLUSION ---
        with st.expander("⚠️ Analyse des résultats aberrants (Outliers)"):
            st.write("L'algorithme a détecté des parties où l'Effort est statistiquement anormal par rapport au reste.")
            if outlier_indices:
                to_exclude = st.multiselect(
                    "Sélectionnez les parties à exclure de l'analyse (indices) :",
                    outlier_indices,
                    format_func=lambda x: f"Scénario {df_filtered.loc[x, 'Scenario']} - Effort: {df_filtered.loc[x, 'Effort']}"
                )
                if to_exclude:
                    df_filtered = df_filtered.drop(to_exclude)
                    st.success(f"{len(to_exclude)} ligne(s) exclue(s).")
            else:
                st.info("Aucune anomalie statistique détectée sur l'Effort.")

        # --- STATISTIQUES ---
        cols = st.columns(4)
        cols[0].metric("Dégâts Moyens", f"{df_filtered['Damage'].mean():.1f}")
        cols[1].metric("Soin Moyen", f"{df_filtered['Healing'].mean():.1f}")
        cols[2].metric("Mitigation Moyenne", f"{df_filtered['Mitigation'].mean():.1f}")
        cols[3].metric("EFFORT CIBLE", f"{df_filtered['Effort'].mean():.1f}")

        # --- GRAPHIQUE AVEC COURBE DE TENDANCE ---
        st.subheader(f"Évolution de la performance (Niveau {level})")
        
        # On utilise une régression pour la courbe de modélisation
        fig = px.scatter(df_filtered, x='Date' if x_axis_mode == "Date" else 'Release State', 
                         y='Effort', color='Release State',
                         trendline="lowess", # Courbe lissée (modélisation)
                         title="Courbe de tendance de l'Effort",
                         template="plotly_dark",
                         hover_data=['Scenario', 'Played By'])
        
        st.plotly_chart(fig, use_container_width=True)

        # --- DÉTAILS ---
        st.subheader("📋 Détail des scénarios")
        st.dataframe(df_filtered[['Date', 'Release State', 'Scenario', 'Damage', 'Healing', 'Mitigation', 'Effort', 'Result']], 
                     use_container_width=True)

else:
    st.info("Veuillez charger le fichier pour commencer.")
