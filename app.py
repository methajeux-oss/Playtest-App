import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuration pour le mode sombre et le layout
st.set_page_config(page_title="Frosthaven Class Analyzer", layout="wide", page_icon="🛡️")

# Injection CSS pour forcer certains styles sombres sur les métriques
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #00d4ff; }
    .stApp { background-color: #0e1117; color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

def load_and_clean(file):
    df = pd.read_csv(file)
    df = df.dropna(subset=['Class', 'Date'])
    df['Date'] = pd.to_datetime(df['Date'])
    # Conversion forcée en numérique pour éviter les erreurs de calcul
    for col in ['Damage', 'Healing', 'Mitigation', 'Class Level']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- APPLICATION DE VOTRE FORMULE D'EFFORT ---
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    return df

st.title("🛡️ Analyseur de Classe : Frosthaven")

uploaded_file = st.sidebar.file_uploader("Charger 'Scenario Tests.csv'", type=['csv'])

if uploaded_file:
    df = load_and_clean(uploaded_file)

    # --- SIDEBAR : FILTRES SIMPLIFIÉS ---
    st.sidebar.header("🎯 Paramètres d'Analyse")

    # 1. Choix de la classe
    classe_selected = st.sidebar.selectbox("Sélectionner la classe", sorted(df['Class'].unique()))

    # 2. Choix UNIQUE du niveau (Comparaison intra-niveau uniquement)
    level_selected = st.sidebar.selectbox("Niveau des tests (X)", range(1, 10), index=0)

    # 3. Mode de comparaison (Axe X des graphiques)
    comp_mode = st.sidebar.radio("Comparer les données par :", ["Date", "Statut (Alpha/Beta/...)"])

    # 4. Filtre de playtesteurs
    playtesters = st.sidebar.multiselect("Playtesteurs", df['Played By'].unique(), default=df['Played By'].unique())

    # --- FILTRAGE ---
    df_filtered = df[
        (df['Class'] == classe_selected) &
        (df['Class Level'] == level_selected) &
        (df['Played By'].isin(playtesters))
    ].sort_values('Date')

    if df_filtered.empty:
        st.warning(f"Aucune donnée trouvée pour {classe_selected} au niveau {level_selected}.")
    else:
        # --- RÉSUMÉ DES STATS (Moyennes & Médianes) ---
        st.subheader(f"Statistiques moyennes : {classe_selected} (Niveau {level_selected})")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Dégâts (Avg)", f"{df_filtered['Damage'].mean():.1f}")
        m2.metric("Soin (Avg)", f"{df_filtered['Healing'].mean():.1f}")
        m3.metric("Mitigation (Avg)", f"{df_filtered['Mitigation'].mean():.1f}")
        m4.metric("EFFORT (Formula)", f"{df_filtered['Effort'].mean():.1f}")

        st.divider()

        # --- GRAPHIQUES ---
        # Définition de l'axe X selon le choix de l'utilisateur
        x_axis = 'Date' if comp_mode == "Date" else 'Release State'

        col_left, col_right = st.columns(2)

        with col_left:
            st.write(f"### Évolution de l'Effort par {comp_mode}")
            fig_effort = px.box(df_filtered, x=x_axis, y='Effort',
                                points="all", color=x_axis,
                                template="plotly_dark",
                                title="Dispersion de l'Effort (Cible : Équilibre)")
            st.plotly_chart(fig_effort, use_container_width=True)

        with col_right:
            st.write(f"### Dégâts vs Mitigation par {comp_mode}")
            # Graphique pour voir si la classe compense ses dégâts par de la survie
            fig_stats = px.bar(df_filtered, x=x_axis, y=['Damage', 'Mitigation', 'Healing'],
                               barmode='group',
                               template="plotly_dark",
                               color_discrete_sequence=['#ff4b4b', '#00d4ff', '#00ff7f'])
            st.plotly_chart(fig_stats, use_container_width=True)

        # --- HISTORIQUE DÉTAILLÉ ---
        with st.expander("Voir le détail des scénarios pour cette sélection"):
            st.table(df_filtered[['Date', 'Release State', 'Played By', 'Scenario', 'Damage', 'Healing', 'Mitigation', 'Effort', 'Result']])

else:
    st.info("En attente du fichier CSV pour analyse.")