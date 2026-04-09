import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    # Conversion numérique incluant la main et la défausse
    cols_to_fix = ['Damage', 'Healing', 'Mitigation', 'Class Level', 'In Hand', 'Discard']
    for col in cols_to_fix:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    # Formule d'Effort
    df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
    return df

st.title("🛡️ Frosthaven Class Lab : Analyse & Comparaison")

uploaded_file = st.sidebar.file_uploader("Fichier CSV", type=['csv'])

if uploaded_file:
    df_raw = load_data(uploaded_file)
    
    # --- FILTRES ---
    st.sidebar.header("🎯 Configuration")
    classe_a = st.sidebar.selectbox("Classe Principale", sorted(df_raw['Class'].unique()))
    comparaison_on = st.sidebar.checkbox("Comparer avec une autre classe")
    classe_b = st.sidebar.selectbox("Classe de comparaison", [c for c in sorted(df_raw['Class'].unique()) if c != classe_a]) if comparaison_on else None

    level = st.sidebar.selectbox("Niveau Unique", range(1, 10))
    x_axis_mode = st.sidebar.radio("Axe temporel :", ["Date", "Release State"])

    def filter_data(cls):
        return df_raw[(df_raw['Class'] == cls) & (df_raw['Class Level'] == level)].copy()

    df_a = filter_data(classe_a)
    df_display = df_a.copy()

    if comparaison_on and classe_b:
        df_b = filter_data(classe_b)
        df_display = pd.concat([df_a, df_b])

    if df_display.empty:
        st.warning("Aucune donnée pour cette sélection.")
    else:
        # --- STATISTIQUES ET GESTION DE MAIN ---
        def show_comprehensive_metrics(df_target, label):
            st.subheader(f"📊 Statistiques : {label}")
            # Ligne 1 : Performance
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Playtests", len(df_target))
            c2.metric("Dégâts (Moy)", f"{df_target['Damage'].mean():.1f}")
            c3.metric("Soin (Moy)", f"{df_target['Healing'].mean():.1f}")
            c4.metric("Mitigation (Moy)", f"{df_target['Mitigation'].mean():.1f}")
            c5.metric("EFFORT", f"{df_target['Effort'].mean():.1f}")

            # Ligne 2 : Gestion de main
            st.markdown(f"**Gestion des cartes (Moyennes / Médianes) pour {label} :**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Main (Moy)", f"{df_target['In Hand'].mean():.1f}")
            m2.metric("Main (Méd)", f"{df_target['In Hand'].median():.1f}")
            m3.metric("Défausse (Moy)", f"{df_target['Discard'].mean():.1f}")
            m4.metric("Défausse (Méd)", f"{df_target['Discard'].median():.1f}")

        show_comprehensive_metrics(df_a, classe_a)
        if comparaison_on and classe_b:
            st.divider()
            show_comprehensive_metrics(df_display[df_display['Class'] == classe_b], classe_b)

        st.divider()

        # --- GRAPHIQUES : RADAR ET ÉVOLUTION ---
        col_radar, col_evol = st.columns([1, 2])

        with col_radar:
            st.subheader("🎯 Profil de Classe")
            categories = ['Damage', 'Healing', 'Mitigation']
            
            fig_radar = go.Figure()
            # Trace Classe A
            fig_radar.add_trace(go.Scatterpolar(
                r=[df_a['Damage'].mean(), df_a['Healing'].mean(), df_a['Mitigation'].mean()],
                theta=categories, fill='toself', name=classe_a, line_color='#00d4ff'
            ))
            # Trace Classe B si besoin
            if comparaison_on and classe_b:
                df_b_radar = df_display[df_display['Class'] == classe_b]
                fig_radar.add_trace(go.Scatterpolar(
                    r=[df_b_radar['Damage'].mean(), df_b_radar['Healing'].mean(), df_b_radar['Mitigation'].mean()],
                    theta=categories, fill='toself', name=classe_b, line_color='#ff4b4b'
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, gridcolor="#444")),
                template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=True
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_evol:
            st.subheader("📈 Évolution de l'Effort")
            color_col = 'Class' if comparaison_on else 'Release State'
            fig_evol = px.scatter(df_display, x='Date' if x_axis_mode == "Date" else 'Release State',  
                                 y='Effort', color=color_col, trendline="lowess", 
                                 template="plotly_dark", hover_data=['Scenario', 'Played By'])
            st.plotly_chart(fig_evol, use_container_width=True)

        # --- DÉTAILS ---
        with st.expander("Voir le détail complet des scénarios"):
            st.dataframe(df_display[['Date', 'Class', 'Scenario', 'In Hand', 'Discard', 'Effort', 'Result']], use_container_width=True)

else:
    st.info("Veuillez charger le fichier pour commencer.")
