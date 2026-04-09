import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Tentative d'import pour la courbe de tendance avancée
try:
    import statsmodels
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Configuration
st.set_page_config(page_title="Frosthaven Class Lab - V1.3", layout="wide")

# Style Dark Mode forcé pour les métriques
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; }
    .stApp { background-color: #0e1117; }
    .stAlert { background-color: #1e1e1e; border: 1px solid #333; }
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

st.title("🛡️ Frosthaven Class Lab : Expertise")

uploaded_file = st.sidebar.file_uploader("Charger 'Scenario Tests.csv'", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- FILTRES SIDEBAR ---
    st.sidebar.header("🎯 Filtres")
    classe = st.sidebar.selectbox("Classe", sorted(df_raw['Class'].unique()))
    level = st.sidebar.selectbox("Niveau Unique", range(1, 10))
    
    min_d, max_d = df_raw['Date'].min().to_pydatetime(), df_raw['Date'].max().to_pydatetime()
    date_range = st.sidebar.date_input("Période d'analyse", [min_d, max_d])
    
    x_axis_mode = st.sidebar.radio("Axe temporel :", ["Date", "Release State"])

    # --- FILTRAGE ---
    mask = (df_raw['Class'] == classe) & (df_raw['Class Level'] == level)
    if len(date_range) == 2:
        mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
    
    df_f = df_raw[mask].copy()

    if not df_f.empty:
        # --- 1. INDICATEURS CLÉS ---
        avg_effort = df_f['Effort'].mean()
        std_effort = df_f['Effort'].std()
        consistency_idx = (std_effort / avg_effort) * 100 if avg_effort != 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Effort Moyen", f"{avg_effort:.2f}")
        c2.metric("Écart-Type", f"{std_effort:.2f}", help="Plus il est élevé, plus les performances varient d'une partie à l'autre.")
        
        status = "Stable" if consistency_idx < 25 else "Irrégulier" if consistency_idx < 45 else "Instable"
        c3.metric("Indice de Consistance", f"{consistency_idx:.1f}%")
        c4.metric("Diagnostic", status)

        st.divider()

        # --- 2. GRAPHIQUE D'ÉVOLUTION AVEC COURBE ---
        st.subheader("📈 Évolution et Modélisation")
        
        # Choix du type de tendance selon la présence de statsmodels
        trend_type = "lowess" if HAS_STATSMODELS else "ols"
        if not HAS_STATSMODELS:
            st.warning("⚠️ Installez 'statsmodels' pour une courbe de tendance lissée. Affichage d'une ligne droite par défaut.")

        fig_evol = px.scatter(df_f, 
                             x='Date' if x_axis_mode == "Date" else 'Release State', 
                             y='Effort', 
                             color='Release State',
                             trendline=trend_type,
                             title=f"Modélisation de l'Effort (Méthode: {trend_type})",
                             template="plotly_dark",
                             hover_data=['Scenario', 'Played By'])
        st.plotly_chart(fig_evol, use_container_width=True)

        # --- 3. ANALYSE DIFFICULTÉ ET JOUEURS ---
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.write("### 📊 Impact de la Difficulté")
            df_diff = df_f.sort_values('Scenario Level')
            fig_diff = px.bar(df_diff, x='Scenario Level', y='Effort', color='Result',
                              title="Effort par Niveau de Scénario",
                              template="plotly_dark", barmode='group')
            st.plotly_chart(fig_diff, use_container_width=True)

        with col_b:
            st.write("### 🔥 Heatmap Playtesteur vs Effort")
            heat_data = df_f.groupby(['Played By', 'Result'])['Effort'].mean().reset_index()
            fig_heat = px.density_heatmap(heat_data, x="Result", y="Played By", z="Effort",
                                          title="Performance Moyenne par Joueur",
                                          color_continuous_scale="Viridis", template="plotly_dark")
            st.plotly_chart(fig_heat, use_container_width=True)

        # --- 4. GESTION DES OUTLIERS & DÉTAILS ---
        with st.expander("🔍 Analyse des anomalies et Détails"):
            Q1, Q3 = df_f['Effort'].quantile(0.25), df_f['Effort'].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df_f[(df_f['Effort'] < (Q1 - 1.5 * IQR)) | (df_f['Effort'] > (Q3 + 1.5 * IQR))]
            
            if not outliers.empty:
                st.write("Parties atypiques détectées :")
                st.table(outliers[['Date', 'Scenario', 'Effort', 'Played By']])
            
            st.write("### Historique Complet")
            st.dataframe(df_f[['Date', 'Scenario', 'Scenario Level', 'Damage', 'Healing', 'Mitigation', 'Effort', 'Result', 'Played By']], use_container_width=True)

else:
    st.info("Veuillez charger le fichier CSV pour lancer l'analyse.")
