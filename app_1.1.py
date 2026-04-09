import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuration
st.set_page_config(page_title="Frosthaven Class Lab", layout="wide")

# Style Dark Mode
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
    if df.empty: return []
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return df[(df[column] < lower_bound) | (df[column] > upper_bound)].index.tolist()

st.title("🛡️ Frosthaven Class Lab : Analyse & Comparaison")

uploaded_file = st.sidebar.file_uploader("Fichier CSV", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- FILTRES SIDEBAR ---
    st.sidebar.header("🎯 Configuration")
    classe_a = st.sidebar.selectbox("Classe Principale", sorted(df_raw['Class'].unique()))
    
    # Option de comparaison
    comparaison_on = st.sidebar.checkbox("Comparer avec une autre classe")
    classe_b = None
    if comparaison_on:
        classe_b = st.sidebar.selectbox("Classe de comparaison", [c for c in sorted(df_raw['Class'].unique()) if c != classe_a])

    level = st.sidebar.selectbox("Niveau Unique", range(1, 10))
    min_d, max_d = df_raw['Date'].min(), df_raw['Date'].max()
    date_range = st.sidebar.date_input("Période d'analyse", [min_d, max_d])
    x_axis_mode = st.sidebar.radio("Axe temporel :", ["Date", "Release State"])

    # --- FILTRAGE ---
    def filter_data(cls):
        m = (df_raw['Class'] == cls) & (df_raw['Class Level'] == level)
        if len(date_range) == 2:
            m &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
        return df_raw[m].copy()

    df_a = filter_data(classe_a)
    df_display = df_a.copy()

    if comparaison_on and classe_b:
        df_b = filter_data(classe_b)
        df_display = pd.concat([df_a, df_b])

    if df_display.empty:
        st.warning("Aucune donnée pour cette sélection.")
    else:
        # --- GESTION DES OUTLIERS (Sur la sélection globale) ---
        outlier_indices = detect_outliers(df_display, 'Effort')
        with st.expander("⚠️ Analyse des résultats aberrants (Outliers)"):
            if outlier_indices:
                to_exclude = st.multiselect(
                    "Exclure de l'analyse :", outlier_indices,
                    format_func=lambda x: f"[{df_display.loc[x, 'Class']}] {df_display.loc[x, 'Scenario']} - Effort: {df_display.loc[x, 'Effort']}"
                )
                if to_exclude:
                    df_display = df_display.drop(to_exclude)
                    df_a = df_display[df_display['Class'] == classe_a]
            else:
                st.info("Aucune anomalie détectée.")

        # --- STATISTIQUES ---
        def show_metrics(df_target, label):
            st.subheader(f"Statistiques : {label}")
            cols = st.columns(5)
            cols[0].metric("Playtests", len(df_target))
            cols[1].metric("Dégâts (Moy)", f"{df_target['Damage'].mean():.1f}")
            cols[2].metric("Soin (Moy)", f"{df_target['Healing'].mean():.1f}")
            cols[3].metric("Mitigation (Moy)", f"{df_target['Mitigation'].mean():.1f}")
            cols[4].metric("EFFORT CIBLE", f"{df_target['Effort'].mean():.1f}")

        show_metrics(df_a, classe_a)
        if comparaison_on and classe_b:
            show_metrics(df_display[df_display['Class'] == classe_b], classe_b)

        # --- GRAPHIQUE UNIQUE ---
        st.divider()
        st.subheader(f"Comparaison de performance (Niveau {level})")
        
        # On colorise par 'Class' si comparaison, sinon par 'Release State'
        color_col = 'Class' if comparaison_on else 'Release State'
        
        fig = px.scatter(
            df_display, 
            x='Date' if x_axis_mode == "Date" else 'Release State',  
            y='Effort', 
            color=color_col,
            trendline="lowess", 
            title="Comparaison des courbes de tendance de l'Effort",
            template="plotly_dark",
            hover_data=['Scenario', 'Played By', 'Class Level']
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # --- DÉTAILS ---
        st.subheader("📋 Historique des données")
        st.dataframe(df_display[['Date', 'Class', 'Release State', 'Scenario', 'Damage', 'Effort', 'Result']], 
                     use_container_width=True)

else:
    st.info("Veuillez charger le fichier pour commencer.")
