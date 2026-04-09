import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuration de la page
st.set_page_config(page_title="Frosthaven Class Lab V1.3", layout="wide", page_icon="⚖️")

# Force le style sombre pour les métriques et l'arrière-plan
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; font-weight: bold; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stTable { background-color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

def load_data(file):
    """Nettoyage et calcul de la formule d'effort."""
    df = pd.read_csv(file)
    df = df.dropna(subset=['Class', 'Date'])
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Conversion numérique stricte
    cols_to_fix = ['Damage', 'Healing', 'Mitigation', 'Class Level']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # --- FORMULE D'EFFORT V1.2 ---
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    return df

st.title("🛡️ Frosthaven Class Lab : Analyseur Expert")

uploaded_file = st.sidebar.file_uploader("Charger le fichier 'Scenario Tests.csv'", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- BARRE LATÉRALE : FILTRES ---
    st.sidebar.header("🎯 Filtres de précision")
    classe = st.sidebar.selectbox("Sélectionner la classe", sorted(df_raw['Class'].unique()))
    level = st.sidebar.selectbox("Niveau de test unique", range(1, 10))
    
    # Calendrier (V1.2)
    min_date_found = df_raw['Date'].min().to_pydatetime()
    max_date_found = df_raw['Date'].max().to_pydatetime()
    date_range = st.sidebar.date_input("Période d'analyse", [min_date_found, max_date_found])
    
    x_axis_mode = st.sidebar.radio("Axe d'évolution :", ["Date", "Release State"])

    # --- FILTRAGE DES DONNÉES ---
    mask = (df_raw['Class'] == classe) & (df_raw['Class Level'] == level)
    if len(date_range) == 2:
        mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
    
    df_f = df_raw[mask].copy()

    if not df_f.empty:
        # --- 1. INDICE DE CONSISTANCE & MÉTRIQUES ---
        st.subheader(f"Analyse de Performance : {classe} (Niveau {level})")
        
        avg_eff = df_f['Effort'].mean()
        std_eff = df_f['Effort'].std()
        # Indice de consistance (Coefficient de variation)
        cons_idx = (std_eff / avg_eff) * 100 if avg_eff != 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Effort Moyen", f"{avg_eff:.2f}")
        c2.metric("Écart-Type (Stabilité)", f"{std_eff:.2f}")
        
        # Diagnostic visuel
        diag = "Stable" if cons_idx < 25 else "Irrégulier" if cons_idx < 45 else "Instable"
        c3.metric("Indice de Consistance", f"{cons_idx:.1f}%")
        c4.metric("Diagnostic Design", diag)

        st.divider()

        # --- 2. MODÉLISATION DE COURBE (LOWESS) ---
        st.subheader("📈 Évolution et Tendances")
        # Utilisation directe de trendline="lowess" sans vérification préalable
        fig_evol = px.scatter(
            df_f, 
            x='Date' if x_axis_mode == "Date" else 'Release State', 
            y='Effort', 
            color='Release State',
            trendline="lowess",
            title=f"Modélisation de l'Effort par {x_axis_mode}",
            template="plotly_dark",
            hover_data=['Scenario', 'Played By', 'Damage']
        )
        st.plotly_chart(fig_evol, use_container_width=True)

        # --- 3. IMPACT DIFFICULTÉ ET JOUEURS ---
        col_left, col_right = st.columns(2)

        with col_left:
            st.write("### 📊 Impact de la Difficulté")
            # Tri naturel des niveaux de scénario (+0, +1, etc.)
            df_diff = df_f.sort_values('Scenario Level')
            fig_diff = px.bar(
                df_diff, x='Scenario Level', y='Effort', color='Result',
                title="Relation Difficulté / Effort / Victoire",
                template="plotly_dark", barmode='group',
                color_discrete_map={'Win': '#00ff7f', 'Loss': '#ff4b4b'}
            )
            st.plotly_chart(fig_diff, use_container_width=True)

        with col_right:
            st.write("### 🔥 Heatmap Playtesteurs")
            # Agrégation pour la Heatmap
            heat_data = df_f.groupby(['Played By', 'Result'])['Effort'].mean().reset_index()
            fig_heat = px.density_heatmap(
                heat_data, x="Result", y="Played By", z="Effort",
                title="Moyenne d'Effort par Joueur et Issue",
                color_continuous_scale="Viridis", template="plotly_dark"
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        # --- 4. ALGORITHME D'OUTLIERS (IQR) & DÉTAILS ---
        with st.expander("🔍 Analyse des anomalies et Données brutes"):
            # Calcul IQR pour l'effort
            Q1 = df_f['Effort'].quantile(0.25)
            Q3 = df_f['Effort'].quantile(0.75)
            IQR = Q3 - Q1
            outliers = df_f[(df_f['Effort'] < (Q1 - 1.5 * IQR)) | (df_f['Effort'] > (Q3 + 1.5 * IQR))]
            
            if not outliers.empty:
                st.warning(f"Attention : {len(outliers)} partie(s) détectée(s) comme statistiquement aberrante(s).")
                st.write("Ces données peuvent fausser vos moyennes (erreurs de règles ou scénarios extrêmes) :")
                st.table(outliers[['Date', 'Scenario', 'Effort', 'Played By', 'Notes:']])
            else:
                st.success("Aucune anomalie statistique détectée.")
            
            st.write("### Historique filtré")
            st.dataframe(df_f[['Date', 'Scenario', 'Scenario Level', 'Damage', 'Healing', 'Mitigation', 'Effort', 'Result', 'Played By', 'Notes:']], use_container_width=True)

else:
    st.info("👋 Bienvenue ! Veuillez charger votre fichier CSV pour commencer l'analyse de classe.")
