import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuration
st.set_page_config(page_title="Frosthaven Pro Analyzer", layout="wide")

# Style Dark Mode forcé
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
    # Conversion numérique
    for col in ['Damage', 'Healing', 'Mitigation', 'Class Level']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Formule d'Effort
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    return df

st.title("🛡️ Frosthaven Class Lab : Expertise")

uploaded_file = st.sidebar.file_uploader("Charger 'Scenario Tests.csv'", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- FILTRES ---
    st.sidebar.header("🎯 Filtres")
    classe = st.sidebar.selectbox("Classe", sorted(df_raw['Class'].unique()))
    level = st.sidebar.selectbox("Niveau Unique", range(1, 10))
    min_d, max_d = df_raw['Date'].min(), df_raw['Date'].max()
    date_range = st.sidebar.date_input("Période", [min_d, max_d])
    
    mask = (df_raw['Class'] == classe) & (df_raw['Class Level'] == level)
    if len(date_range) == 2:
        mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
    
    df_f = df_raw[mask].copy()

    if not df_f.empty:
        # --- 1. INDICE DE CONSISTANCE ---
        st.subheader("📊 Diagnostic de Stabilité")
        avg_effort = df_f['Effort'].mean()
        std_effort = df_f['Effort'].std()
        # Coefficient de variation (CV) : plus il est bas, plus la classe est stable
        consistency_idx = (std_effort / avg_effort) * 100 if avg_effort != 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Effort Moyen", f"{avg_effort:.1f}")
        c2.metric("Écart-Type", f"{std_effort:.1f}")
        
        # Interprétation de la consistance
        status = "Stable" if consistency_idx < 20 else "Swingy (Aléatoire)" if consistency_idx < 40 else "Instable"
        c3.metric("Indice de Consistance", f"{consistency_idx:.1f}%", help="Plus l'indice est bas, plus les performances sont prévisibles.")
        c4.metric("Fiabilité", status)

        st.divider()

        # --- 2. IMPACT DE LA DIFFICULTÉ & HEATMAP ---
        col_diff, col_heat = st.columns(2)

        with col_diff:
            st.write("### 📈 Impact de la Difficulté")
            # Tri pour avoir +0, +1, +2 dans l'ordre
            df_f = df_f.sort_values('Scenario Level')
            fig_diff = px.bar(df_f, x='Scenario Level', y='Effort', 
                              color='Result',
                              title="Effort par Modificateur de Scénario",
                              labels={'Scenario Level': 'Difficulté (ex: +0, +1)', 'Effort': 'Effort Moyen'},
                              template="plotly_dark",
                              barmode='group')
            st.plotly_chart(fig_diff, use_container_width=True)

        with col_heat:
            st.write("### 🔥 Heatmap Playtesteur vs Succès")
            # Pivot pour la heatmap : Playtesteur en Y, Résultat en X, Effort en couleur
            heat_data = df_f.groupby(['Played By', 'Result'])['Effort'].mean().reset_index()
            fig_heat = px.density_heatmap(heat_data, x="Result", y="Played By", z="Effort",
                                          title="Effort Moyen par Joueur et Résultat",
                                          color_continuous_scale="Viridis",
                                          template="plotly_dark")
            st.plotly_chart(fig_heat, use_container_width=True)

        # --- 3. DÉTECTION D'OUTLIERS (VOTRE DEMANDE PRÉCÉDENTE) ---
        with st.expander("🔍 Gestion des résultats aberrants"):
            Q1, Q3 = df_f['Effort'].quantile(0.25), df_f['Effort'].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df_f[(df_f['Effort'] < (Q1 - 1.5 * IQR)) | (df_f['Effort'] > (Q3 + 1.5 * IQR))]
            
            if not outliers.empty:
                st.write("Parties détectées comme statistiquement anormales :")
                st.dataframe(outliers[['Date', 'Scenario', 'Effort', 'Played By']])
                st.info("Conseil : Si ces parties sont dues à une erreur de règle ou un scénario très spécifique, ignorez-les dans votre analyse finale.")
            else:
                st.success("Toutes les données sont cohérentes.")

        # --- DÉTAILS ---
        st.subheader("📋 Historique des tests")
        st.dataframe(df_f[['Date', 'Scenario', 'Scenario Level', 'Damage', 'Healing', 'Mitigation', 'Effort', 'Result', 'Played By']], use_container_width=True)

else:
    st.info("Veuillez charger le fichier pour activer l'expertise.")
