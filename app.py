import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import calendar

# 1. PAGE CONFIGURATION
CCUG_LOGO_URL = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/icons/CCUG.png"
st.set_page_config(page_title="Playtest App V2.4", layout="wide", page_icon=CCUG_LOGO_URL)

# 2. ICON & CSS CONFIG
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/methajeux-oss/Playtest-App/main/"
GITHUB_ICON_BASE = f"{GITHUB_RAW_BASE}icons/"

def get_icon_url(class_name):
    if pd.isna(class_name) or class_name == "" or class_name == "🏠 Homepage": return ""
    clean_name = str(class_name).strip().replace(" ", "%20")
    return f"{GITHUB_ICON_BASE}{clean_name}.png"

st.markdown(f"""
    <style>
    [data-testid="stMetricValue"] {{ color: #00d4ff; font-size: 1.2rem; }}
    .icon-container {{
        width: 70px; height: 70px; display: flex; align-items: center; justify-content: center;
        overflow: hidden; border-radius: 8px; background-color: rgba(127, 127, 127, 0.1);
    }}
    .icon-container img {{ width: 100%; height: 100%; object-fit: contain; }}
    </style>
    """, unsafe_allow_html=True)

# 3. DATA ENGINE
SCENARIO_GID = "0"
CAMPAIGN_GID = "718802502"
BASE_URL = "https://docs.google.com/spreadsheets/d/1Do0i-lWf54aGONfR82OYEKLn1kxHAmPfrTj9UYngz3c/export?format=csv&gid="
LINKS_URL = f"{GITHUB_RAW_BASE}class_links.csv"

@st.cache_data(ttl=300)
def load_data(source, is_scenario=True):
    try:
        df = pd.read_csv(source)
        df.columns = [str(c).strip() for c in df.columns]
        
        # NORMALISATION DE LA CASSE POUR ÉVITER LES DOUBLONS
        for col in ['Class', 'Played By', 'Scenario', 'Release State']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()
                df[col] = df[col].replace('Nan', np.nan) # Rétablit les vrais NaN si nécessaire
                
        df = df.dropna(subset=['Class'])
        if df.empty: 
            return pd.DataFrame()

        if is_scenario:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            for c in ['Damage', 'Healing', 'Mitigation', 'Class Level', 'Scenario Level', 'In Hand', 'Discard', 'Rounds']:
                if c in df.columns: 
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            df['Effort'] = df['Damage'] + (df['Healing'] + df['Mitigation']) * 0.75
            df['Icon URL'] = df['Class'].apply(get_icon_url)

            df['sid'] = df['Test Result Link'].fillna(df['Date'].astype(str) + df['Scenario'])
            df['Scenario Rank'] = df.groupby('sid')['Effort'].rank(ascending=False, method='min')
            df['Group Size'] = df.groupby('sid')['Class'].transform('count')
            df['Rank String'] = df['Scenario Rank'].fillna(0).astype(int).astype(str) + " / " + df['Group Size'].fillna(0).astype(int).astype(str)
        else:
            df['Icon URL'] = df['Class'].apply(get_icon_url)
            
        return df
        
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_links():
    try:
        df = pd.read_csv(LINKS_URL, sep=';')
        df.columns = [c.strip() for c in df.columns]
        if 'Class' in df.columns:
            df['Class'] = df['Class'].astype(str).str.strip().str.title()
        return df
    except:
        return pd.DataFrame()

VOTERS_URL = f"{GITHUB_RAW_BASE}voters.csv"
@st.cache_data(ttl=600)
def load_voters():
    try:
        df = pd.read_csv(VOTERS_URL)
        return [str(v).strip().title() for v in df.iloc[:,0].tolist()]
    except:
        return []
        
# --- FICHIER ÉVÉNEMENTS ---
EVENTS_URL = f"{GITHUB_RAW_BASE}events.csv"

@st.cache_data(ttl=600)
def load_events():
    try:
        df = pd.read_csv(EVENTS_URL)
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        df['End Date'] = pd.to_datetime(df.get('End Date'), errors='coerce').fillna(df['Start Date'])
        return df.dropna(subset=['Start Date', 'Event'])
    except:
        return pd.DataFrame(columns=['Start Date', 'End Date', 'Event', 'Type'])

# 4. SIDEBAR
st.sidebar.header("📂 Connexion des Données")
data_mode = st.sidebar.radio("Source :", ["Google Sheets", "Manual Upload"])
df_events = load_events()

if data_mode == "Google Sheets":
    df_raw = load_data(BASE_URL + SCENARIO_GID)
    df_campaigns = load_data(BASE_URL + CAMPAIGN_GID, is_scenario=False)
    df_links = load_links()
else:
    file_scen = st.sidebar.file_uploader("Upload Scenario CSV", type=['csv'])
    df_raw = load_data(file_scen) if file_scen else pd.DataFrame()
    df_campaigns = pd.DataFrame()
    df_links = pd.DataFrame()

if df_raw.empty:
    st.info("Veuillez connecter une source de données.")
    st.stop()

# --- FILTERS LOGIC ---
class_list = ["🏠 Homepage"] + sorted([str(c) for c in df_raw['Class'].dropna().unique()])
class_a = st.sidebar.selectbox("Classe Principale", class_list)

compare_mode = False
class_b = None
level_filter = "Tous"
date_range = [df_raw['Date'].min(), df_raw['Date'].max()]

if class_a != "🏠 Homepage":
    st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_a)}"></div>', unsafe_allow_html=True)
    compare_mode = st.sidebar.checkbox("Mode Comparaison")
    if compare_mode:
        class_b = st.sidebar.selectbox("Classe Secondaire", [c for c in class_list if c not in [class_a, "🏠 Homepage"]])
        st.sidebar.markdown(f'<div class="icon-container"><img src="{get_icon_url(class_b)}"></div>', unsafe_allow_html=True)
    
    level_filter = st.sidebar.selectbox("Niveau d'Analyse", ["Tous"] + list(range(1, 10)))
    date_range = st.sidebar.date_input("Période", [df_raw['Date'].min(), df_raw['Date'].max()])

# 5. PROCESSING
if class_a != "🏠 Homepage":
    def get_filtered(cls, lvl=None):
        if cls is None: return pd.DataFrame()
        mask = (df_raw['Class'] == cls)
        if lvl and lvl != "Tous": mask &= (df_raw['Class Level'] == lvl)
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            mask &= (df_raw['Date'].dt.date >= date_range[0]) & (df_raw['Date'].dt.date <= date_range[1])
        return df_raw[mask].copy()

    df_a = get_filtered(class_a, level_filter)
    df_a_all = get_filtered(class_a)
    df_b = get_filtered(class_b, level_filter) if compare_mode else pd.DataFrame()
    df_b_all = get_filtered(class_b) if compare_mode else pd.DataFrame()

# 6. MAIN LAYOUT
if class_a == "🏠 Homepage":
    st.title("🏠 CCUG Playtest Portal")
    df_raw['Month_Year'] = df_raw['Date'].dt.strftime('%B %Y')
    
    current_month_str = pd.Timestamp.now().strftime('%B %Y')
    existing_months = list(df_raw.sort_values('Date', ascending=False)['Month_Year'].unique())
    
    if current_month_str not in existing_months:
        month_options = [current_month_str] + existing_months
        default_index = 0
    else:
        month_options = existing_months
        default_index = month_options.index(current_month_str)
        
    selected_month = st.selectbox("📅 Choisir le mois à analyser", month_options, index=default_index)
    
    df_m = df_raw[df_raw['Month_Year'] == selected_month]
    selected_dt = pd.to_datetime(selected_month, format='%B %Y')

    st.header(f"🚀 Top 3 des classes les plus jouées ({selected_month})")
    c1, c2, c3 = st.columns(3)
    CAT_COLORS = {"Conceptual": "#d3d3d3", "Alpha": "#ff4b4b", "Beta": "#90ee90"}

    for cat_name, col in [("Conceptual", c1), ("Alpha", c2), ("Beta", c3)]:
        with col:
            st.subheader(cat_name)
            top_cat = df_m[df_m['Release State'].str.strip().str.title() == cat_name]['Class'].value_counts().head(3)
            if not top_cat.empty:
                for i, (name, count) in enumerate(top_cat.items()):
                    st.markdown(f'<div style="background:{CAT_COLORS[cat_name]}; color:black; padding:10px; border-radius:5px; margin-bottom:5px;"><strong>#{i+1} {name}</strong><br><small>{count} sessions</small></div>', unsafe_allow_html=True)
            else: 
                st.info("Aucune donnée")

    st.divider()

    col_top1, col_top2 = st.columns(2)
    with col_top1:
        st.header("🏆 Top 3 Testeurs (Volume)")
        top_testers = df_m['Played By'].value_counts().head(3)
        for i, (name, count) in enumerate(top_testers.items()):
            st.metric(label=f"#{i+1} Plus de sessions", value=name, delta=f"{count} tests")

    with col_top2:
        st.header("🎭 Top 3 Polyvalence")
        top_versatile = df_m.groupby('Played By')['Class'].nunique().sort_values(ascending=False).head(3)
        for i, (name, count) in enumerate(top_versatile.items()):
            st.metric(label=f"#{i+1} Plus de classes", value=name, delta=f"{count} classes")

    st.divider()
    st.header("🔍 Classes en quête de visibilité")
    st.caption("Classes jouées le mois dernier et ce mois-ci, mais avec le plus faible volume de tests actuellement.")

    prev_month_dt = selected_dt - pd.DateOffset(months=1)
    prev_month_str = prev_month_dt.strftime('%B %Y')

    classes_this_month = set(df_m['Class'].unique())
    classes_last_month = set(df_raw[df_raw['Date'].dt.strftime('%B %Y') == prev_month_str]['Class'].unique())
    active_classes = list(classes_this_month.intersection(classes_last_month))

    if not active_classes:
        st.info("Il n'y a pas assez de données sur les deux derniers mois pour effectuer cette analyse.")
    else:
        df_visibility = df_m[df_m['Class'].isin(active_classes)]
        low_cols = st.columns(3)
        for idx, cat_name in enumerate(["Conceptual", "Alpha", "Beta"]):
            with low_cols[idx]:
                st.subheader(cat_name)
                cat_filter = df_visibility[df_visibility['Release State'].str.strip().str.title() == cat_name]
                bottom_classes = cat_filter['Class'].value_counts(ascending=True).head(3)
                if not bottom_classes.empty:
                    for name, count in bottom_classes.items():
                        st.markdown(f"""
                            <div style="border: 1px solid {CAT_COLORS[cat_name]}; padding:8px; border-radius:5px; margin-bottom:5px; opacity: 0.8;">
                                <span style="color:{CAT_COLORS[cat_name]}; font-weight:bold;">{name}</span><br>
                                <small>{count} session(s) ce mois-ci</small>
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.write("N/A")

    st.divider()
    st.header(f"📅 Agenda CCUG - {selected_month}")

    year, month = selected_dt.year, selected_dt.month

    cal = calendar.Calendar(firstweekday=0)
    month_days = list(cal.itermonthdays(year, month))
    day_names = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

    st.markdown("""
    <style>
        .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; background-color: #262730; padding: 10px; border-radius: 10px; }
        .calendar-header { text-align: center; font-weight: bold; color: #00d4ff; padding-bottom: 5px; font-size: 0.9em; }
        .calendar-day { min-height: 90px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 5px; padding: 5px; }
        .day-number { font-size: 0.8em; opacity: 0.5; margin-bottom: 5px; }
        .event-bar { font-size: 0.7em; background: #00d4ff; color: black; padding: 2px 4px; border-radius: 3px; margin-bottom: 2px; font-weight: bold; line-height: 1.1; overflow: hidden; }
        .event-beta { background: #90ee90; }
        .event-alpha { background: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(7)
    for i, name in enumerate(day_names):
        cols[i].markdown(f"<div class='calendar-header'>{name}</div>", unsafe_allow_html=True)

    html_grid = '<div class="calendar-grid">'
    for day in month_days:
        if day == 0:
            html_grid += '<div class="calendar-day" style="opacity:0;"></div>'
        else:
            current_date = pd.Timestamp(year, month, day)
            day_events = df_events[
                (df_events['Start Date'].dt.date <= current_date.date()) & 
                (df_events['End Date'].dt.date >= current_date.date())
            ]
            events_html = ""
            for _, ev in day_events.iterrows():
                etype = str(ev.get('Type', '')).lower()
                e_class = f"event-{etype}" if etype in ['beta', 'alpha'] else ""
                events_html += f'<div class="event-bar {e_class}">{ev["Event"]}</div>'
            
            html_grid += f'<div class="calendar-day"><div class="day-number">{day}</div>{events_html}</div>'
    html_grid += '</div>'
    st.markdown(html_grid, unsafe_allow_html=True)

else:
    col_tabs, col_disc = st.columns([0.85, 0.15])
    
    # ONGLETS SANS LE MENU PARAMÈTRES
    tab_dash, tab_road, tab_testers = st.tabs(["📊 Log des Scénarios", "🎯 Roadmap de Tests", "👥 Testers"])

    with col_disc:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if not df_links.empty:
            link_row = df_links[df_links['Class'] == class_a]
            if not link_row.empty:
                st.link_button(f"💬 Discord", link_row['Discord'].values[0], use_container_width=True)
    
    # Onglet DASHBOARD
    with tab_dash:
        if df_a.empty:
            st.warning("Aucune donnée trouvée pour le niveau sélectionné.")
        else:
            release_state = str(df_a_all.sort_values('Date').iloc[-1]['Release State']).strip().title() if not df_a_all.empty else ""
            priority_levels = {"Conceptual": "Niveau 1", "Alpha": "Niveaux 1 - 5", "Beta": "Niveaux 1 - 9", "Official": "Tous", "Release": "Tous"}
            target = priority_levels.get(release_state, "Tous")
            st.info(f"🎯 **Priorité de Test :** **{target}** (État Actuel: {release_state})")

            with st.expander("⚠️ Gestion des Valeurs Aberrantes"):
                df_pool = pd.concat([df_a, df_b])
                if len(df_pool) >= 4:
                    Q1, Q3 = df_pool['Effort'].quantile(0.25), df_pool['Effort'].quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = df_pool[(df_pool['Effort'] < Q1 - 1.5*IQR) | (df_pool['Effort'] > Q3 + 1.5*IQR)].index.tolist()
                    to_drop = st.multiselect("Exclure de l'analyse :", outliers, format_func=lambda x: f"{df_pool.loc[x, 'Scenario']} (Effort: {df_pool.loc[x, 'Effort']})")
                    df_a = df_a.drop([i for i in to_drop if i in df_a.index])
                    if compare_mode: df_b = df_b.drop([i for i in to_drop if i in df_b.index])

            # Affichage des métriques toujours actif
            def render_stats(df, df_full, name):
                col_img, col_txt = st.columns([1, 12])
                with col_img: st.markdown(f'<div class="icon-container"><img src="{get_icon_url(name)}"></div>', unsafe_allow_html=True)
                with col_txt: st.subheader(f"{name} - Niveau {level_filter}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Playtests", len(df))
                c2.metric("Testeurs Uniques", df['Played By'].nunique())
                c3.metric("Effort Moyen", f"{df['Effort'].mean():.1f}")
                c4.metric("Rang Global", f"{df_full['Scenario Rank'].mean():.2f}")
                c5, c6, c7, c8 = st.columns(4)
                c5.metric(f"Dégâts (Moy/Méd)", f"{df['Damage'].mean():.1f} / {df['Damage'].median():.1f}")
                c6.metric(f"Soin (Moy/Méd)", f"{df['Healing'].mean():.1f} / {df['Healing'].median():.1f}")
                c7.metric(f"Mitigation (Moy/Méd)", f"{df['Mitigation'].mean():.1f} / {df['Mitigation'].median():.1f}")
                c8.metric("Main/Défausse (Moy)", f"{df['In Hand'].mean():.1f} / {df['Discard'].mean():.1f}")

            render_stats(df_a, df_a_all, class_a)
            if compare_mode and not df_b.empty:
                st.divider()
                render_stats(df_b, df_b_all, class_b)

            # Affichage des graphiques toujours actif
            st.divider()
            c_rad, c_evol = st.columns([1, 2])
            with c_rad:
                st.write(f"**Signature du Rôle**")
                radar_cols = ['Damage', 'Healing', 'Mitigation']
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatterpolar(r=[df_a[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_a, line_color='#00d4ff'))
                if compare_mode and not df_b.empty:
                    fig_r.add_trace(go.Scatterpolar(r=[df_b[c].mean() for c in radar_cols], theta=radar_cols, fill='toself', name=class_b, line_color='#ff4b4b'))
                fig_r.update_layout(polar=dict(radialaxis=dict(visible=True)), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_r, use_container_width=True)
            
            with c_evol:
                st.write(f"**Modélisation de l'Effort (Modulable & Scientifique)**")
                df_chart_base = pd.concat([df_a_all, df_b_all]) if compare_mode else df_a_all
                
                if not df_chart_base.empty:
                    df_chart = df_chart_base.copy()
                    
                    def check_win_status(val):
                        v = str(val).strip().lower()
                        if any(w in v for w in ['win', 'gagné', 'gagne', 'victoire']):
                            return "Gagné"
                        return "Perdu / Abandonné"
                    
                    df_chart['Statut_Resultat'] = df_chart['Result'].apply(check_win_status)
                    
                    df_chart['Rounds'] = pd.to_numeric(df_chart['Rounds'], errors='coerce').replace(0, np.nan)
                    df_chart['Scenario Level'] = pd.to_numeric(df_chart['Scenario Level'], errors='coerce').fillna(0)
                    
                    multiplicateur = np.ceil(df_chart['Class Level'] / 2) + df_chart['Scenario Level']
                    multiplicateur = np.maximum(1, multiplicateur)
                    
                    df_chart['Effort/Round'] = df_chart['Effort'] / (df_chart['Rounds'] * multiplicateur)
                    
                    metric_options = {
                        "Effort": "Effort", 
                        "Rang": "Scenario Rank", 
                        "Dégâts": "Damage", 
                        "Soin": "Healing", 
                        "Mitigation": "Mitigation",
                        "Effort / Round": "Effort/Round"
                    }
                    default_y = list(metric_options.keys()).index("Effort / Round")
                    selected_metric_label = st.selectbox("Métrique (Axe Y)", list(metric_options.keys()), index=default_y)
                    y_column = metric_options[selected_metric_label]
                    
                    x_options = ["Temps (Mois)", "Vision Globale Interniveau (1-9)", "Niveau Spécifique (1-9)"]
                    default_x = x_options.index("Vision Globale Interniveau (1-9)")
                    x_view = st.selectbox("Dimension (Axe X)", x_options, index=default_x)
                    
                    if x_view == "Niveau Spécifique (1-9)":
                        specific_lvl = st.selectbox("Choisir le niveau précis", list(range(1, 10)))
                        df_plot = df_chart[df_chart['Class Level'] == specific_lvl].sort_values('Date')
                        x_column = 'Date'
                    elif x_view == "Vision Globale Interniveau (1-9)":
                        df_plot = df_chart[(df_chart['Class Level'] >= 1) & (df_chart['Class Level'] <= 9)].sort_values('Class Level')
                        x_column = 'Class Level'
                    else:
                        df_plot = df_chart.sort_values('Date')
                        x_column = 'Date'
                    
                    if df_plot.empty:
                        st.info("Aucune donnée pour cette configuration d'axes.")
                    else:
                        fig_m = go.Figure()
                        color_points = {"Gagné": "#2ecc71", "Perdu / Abandonné": "#e74c3c"}
                        unique_classes = df_plot['Class'].unique()
                        
                        for cls in unique_classes:
                            df_cls = df_plot[df_plot['Class'] == cls].sort_values(by=x_column)
                            
                            fig_m.add_trace(go.Scatter(
                                x=df_cls[x_column],
                                y=df_cls[y_column],
                                mode='lines',
                                name=f"Données : {cls}",
                                line=dict(width=1.5),
                                opacity=0.5,
                                showlegend=True
                            ))
                            
                            df_fit = df_cls.dropna(subset=[x_column, y_column])
                            if len(df_fit) > 1:
                                try:
                                    x_fit_num = pd.to_numeric(df_fit[x_column]) if x_column == 'Date' else df_fit[x_column]
                                    y_fit = df_fit[y_column]
                                    
                                    coefs = np.polyfit(x_fit_num, y_fit, 1)
                                    poly_func = np.poly1d(coefs)
                                    
                                    x_model_num = np.linspace(x_fit_num.min(), x_fit_num.max(), 100)
                                    y_model = poly_func(x_model_num)
                                    x_model_plot = pd.to_datetime(x_model_num) if x_column == 'Date' else x_model_num
                                    
                                    fig_m.add_trace(go.Scatter(
                                        x=x_model_plot,
                                        y=y_model,
                                        mode='lines',
                                        name=f"Modèle (Régression) : {cls}",
                                        line=dict(dash='dash', width=2.5),
                                        showlegend=True
                                    ))
                                except Exception:
                                    pass
                            
                            for status, hex_color in color_points.items():
                                df_status = df_cls[df_cls['Statut_Resultat'] == status]
                                if not df_status.empty:
                                    fig_m.add_trace(go.Scatter(
                                        x=df_status[x_column],
                                        y=df_status[y_column],
                                        mode='markers',
                                        name=f"{cls} ({status})",
                                        marker=dict(color=hex_color, size=10, symbol='circle', line=dict(width=1, color='white')),
                                        hovertemplate=f"<b>Classe :</b> {cls}<br><b>X :</b> %{{x}}<br><b>Y :</b> %{{y}}<br><b>Résultat :</b> {status}<extra></extra>",
                                        showlegend=True
                                    ))
                                    
                        fig_m.update_layout(
                            template="plotly_dark",
                            xaxis_title=str(x_view),
                            yaxis_title=str(selected_metric_label),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)'
                        )
                        
                        if x_column == 'Class Level':
                            fig_m.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=1))
                            
                        st.plotly_chart(fig_m, use_container_width=True)
                        
            # Affichage de la table toujours actif
            st.divider()
            st.subheader("📋 Données Détaillées")
            df_table = (pd.concat([df_a, df_b]) if compare_mode else df_a).copy()

            df_table['Rounds'] = pd.to_numeric(df_table['Rounds'], errors='coerce').replace(0, np.nan)
            df_table['Scenario Level'] = pd.to_numeric(df_table['Scenario Level'], errors='coerce').fillna(0)
            
            multiplicateur_tbl = np.ceil(df_table['Class Level'] / 2) + df_table['Scenario Level']
            multiplicateur_tbl = np.maximum(1, multiplicateur_tbl)
            
            df_table['Effort/Round'] = df_table['Effort'] / (df_table['Rounds'] * multiplicateur_tbl)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Effort Médian / Round", f"{df_table['Effort/Round'].median():.2f}")
            with col_m2:
                st.metric("Effort Moyen / Round", f"{df_table['Effort/Round'].mean():.2f}")

            st.dataframe(
                df_table.sort_values('Date', ascending=False),
                column_order=("Icon URL", "Date", "Class", "Scenario", "Rank String", "Effort", "Effort/Round", "Result"),
                column_config={
                    "Icon URL": st.column_config.ImageColumn("Icon", width="small"),
                    "Effort/Round": st.column_config.NumberColumn("Effort/R", format="%.2f")
                },
                width="stretch",
                hide_index=True
            )

    # Onglet ROADMAP
    with tab_road:
        st.header("Roadmap de Tests")
        col_c1, col_c2 = st.columns(2)
        df_camp_a = df_campaigns[df_campaigns['Class'] == class_a] if not df_campaigns.empty else pd.DataFrame()
        with col_c1: st.metric(f"Sessions en Campagne ({class_a})", len(df_camp_a))
        df_camp_b = pd.DataFrame()
        if compare_mode:
            df_camp_b = df_campaigns[df_campaigns['Class'] == class_b] if not df_campaigns.empty else pd.DataFrame()
            with col_c2: st.metric(f"Sessions en Campagne ({class_b})", len(df_camp_b))

        df_camp_total = pd.concat([df_camp_a, df_camp_b]) if compare_mode else df_camp_a
        if not df_camp_total.empty:
            st.subheader("📋 Log des Tests en Campagne")
            st.dataframe(
                df_camp_total,
                column_order=("Icon URL", "Class", "Played By", "Starting Level", "Ending Level"),
                column_config={"Icon URL": st.column_config.ImageColumn("Icon", width="small")},
                use_container_width=True, hide_index=True
            )

        st.divider()
        st.subheader("Couverture des données par niveau")
        cov_a = pd.DataFrame([{"Level": l, "Tests": len(df_a_all[df_a_all['Class Level'] == l]), "Class": class_a} for l in range(1, 10)])
        if compare_mode:
            cov_b = pd.DataFrame([{"Level": l, "Tests": len(df_b_all[df_b_all['Class Level'] == l]), "Class": class_b} for l in range(1, 10)])
            df_cov_plot = pd.concat([cov_a, cov_b])
            fig_cov = px.bar(df_cov_plot, x='Level', y='Tests', color='Class', barmode='group', color_discrete_sequence=['#00d4ff', '#ff4b4b'])
        else:
            fig_cov = px.bar(cov_a, x='Level', y='Tests', color_discrete_sequence=['#00d4ff'])
        fig_cov.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(dtick=1))
        st.plotly_chart(fig_cov, use_container_width=True)

        col_m1, col_m2 = st.columns(2)
        def get_missing_msg(df_all, name):
            missing = [str(l) for l in range(1, 10) if len(df_all[df_all['Class Level'] == l]) == 0]
            return f":red[**{name}** - Niveaux manquants : {', '.join(missing)}]" if missing else f":green[**{name}** - Tous les niveaux sont testés !]"
        with col_m1: st.markdown(get_missing_msg(df_a_all, class_a))
        if compare_mode:
            with col_m2: st.markdown(get_missing_msg(df_b_all, class_b))

    # Onglet TESTERS
    with tab_testers:
        st.header(f"👥 Statistiques des testeurs ({class_a})")

        if df_a_all.empty:
            st.warning("Aucune donnée disponible pour cette classe.")
        else:
            voters_list = load_voters()

            tester_stats = df_a_all.groupby('Played By').agg({
                'Date': 'count',
                'Class Level': lambda x: sorted(list(x.unique()))
            }).reset_index()

            tester_stats.columns = ['Tester', 'Sessions', 'Niveaux']
            tester_stats['Voter'] = tester_stats['Tester'].apply(
                lambda x: "⭐ Voter" if str(x).strip().title() in voters_list else "❌"
            )

            st.dataframe(
                tester_stats.sort_values('Sessions', ascending=False),
                column_config={
                    "Sessions": st.column_config.NumberColumn("Nombre de tests", help="Sessions totales jouées"),
                    "Niveaux": st.column_config.ListColumn("Niveaux testés"),
                    "Voter": st.column_config.TextColumn("Statut Voter")
                },
                use_container_width=True,
                hide_index=True
            )

            st.divider()
            st.subheader(f"🤝 Classes testées avec {class_a}")

            sids_with_a = df_a_all['sid'].unique()
            df_companions = df_raw[(df_raw['sid'].isin(sids_with_a)) & (df_raw['Class'] != class_a)]

            if not df_companions.empty:
                companion_states = df_raw.groupby('Class')['Release State'].last().to_dict()
                companions = sorted(df_companions['Class'].unique())

                STATE_ORDER = ["Official", "Released", "Beta", "Alpha", "Conceptual"]
                COLOR_MAP = {
                    "Released": "#add8e6", "Beta": "#90ee90", "Alpha": "#ff4b4b",
                    "Conceptual": "#d3d3d3", "Official": "#a333c8"
                }

                for state in STATE_ORDER:
                    classes_in_state = [c for c in companions if companion_states.get(c) == state]
                    if classes_in_state:
                        st.markdown(f"#### {state}s")
                        cols = st.columns(4)
                        for idx, comp_name in enumerate(classes_in_state):
                            bg_color = COLOR_MAP.get(state, "#ffffff")
                            text_color = "black" if state != "Official" else "white"
                            with cols[idx % 4]:
                                st.markdown(
                                    f"""<div style="background-color:{bg_color}; color:{text_color};
                                    padding:8px; border-radius:5px; margin-bottom:10px;
                                    text-align:center; font-weight:bold; font-size:0.85em; border: 1px solid rgba(0,0,0,0.1);">
                                    {comp_name}
                                    </div>""",
                                    unsafe_allow_html=True
                                )
            else:
                st.info("Aucune classe partenaire trouvée.")
