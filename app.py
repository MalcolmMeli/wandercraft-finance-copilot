"""
Wandercraft Finance Copilot — V2
Prototype d'automatisation du controle comptable.

Preuve de concept couvrant les cycles fournisseurs, banque et cloture. L'outil
detecte les anomalies, prepare les traitements, trace les decisions et laisse la
validation au comptable. Positionnement : prototype metier, non un produit fini.

Principe directeur : l'IA propose, l'humain valide et trace sa decision.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import controles as ctrl
import rapprochement as rap
import cloture as clo
import relances as rel
import audit

st.set_page_config(page_title="Wandercraft Finance Copilot", page_icon="WC",
                   layout="wide", initial_sidebar_state="expanded")

# Palette premium (alignee sur les maquettes)
INDIGO = "#4F46E5"; INDIGO_L = "#6366F1"; ENCRE = "#0F1E38"
VERT = "#0F9F6E"; AMBRE = "#D97706"; CORAIL = "#E5484D"; GRIS = "#7A889E"
# Alias pour compatibilite avec le reste du code
BLEU = INDIGO; ROUGE = CORAIL; ORANGE = AMBRE; ARDOISE = ENCRE

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
    .stApp { background-color: #FAFBFD; }
    .main .block-container { padding-top: 2.2rem; max-width: 1250px; }

    /* Titres */
    h1 { color: #0F1E38 !important; font-weight: 800 !important; letter-spacing: -0.5px; font-size: 1.9rem !important; }
    h2 { color: #0F1E38 !important; font-weight: 700 !important; }
    h3 { color: #0F1E38 !important; font-weight: 700 !important; }

    /* Cartes KPI (st.metric) */
    [data-testid="stMetric"] {
        background: white; border: 1px solid #E8EBF2; border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(15,30,56,0.03), 0 6px 20px rgba(15,30,56,0.035);
    }
    [data-testid="stMetricLabel"] {
        font-size: 11px !important; color: #7A889E !important; text-transform: uppercase;
        letter-spacing: 0.5px; font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px !important; color: #0F1E38 !important; font-weight: 800 !important;
        letter-spacing: -0.5px; font-variant-numeric: tabular-nums;
    }
    [data-testid="stMetricDelta"] { font-size: 12px !important; font-weight: 600 !important; }

    /* Sidebar premium */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F1E38 0%, #14213D 100%);
    }
    [data-testid="stSidebar"] * { color: #C4CDDE !important; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: white !important; }
    [data-testid="stSidebar"] .stRadio label { color: #A9B4CA !important; font-size: 13.5px; }
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] { color: white !important; font-size: 20px !important; }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] { color: #8B98B0 !important; }

    /* Bandeaux (st.info / st.success / st.warning) */
    [data-testid="stAlert"] { border-radius: 12px; border: none; }

    /* Titre de section personnalise */
    .titre-section {
        border-left: 3px solid #4F46E5; padding-left: 12px; margin: 10px 0 14px 0;
        font-weight: 700; color: #0F1E38; font-size: 15px;
    }

    /* Badges */
    .pill { display:inline-block; padding:3px 11px; border-radius:999px; font-size:11px; font-weight:600; }
    .pill-grey { background:#EEF1F6; color:#64748B; }
    .pill-amber { background:#FEF3E2; color:#B45309; }
    .pill-green { background:#E3F5EE; color:#0B7A54; }
    .pill-slate { background:#EAECF2; color:#5A6A84; }
    .pill-red { background:#FDECEC; color:#C0343A; }

    /* Boutons */
    .stButton button {
        background: #4F46E5; color: white; border: none; border-radius: 9px;
        font-weight: 600; padding: 8px 18px; box-shadow: 0 2px 8px rgba(79,70,229,0.25);
    }
    .stButton button:hover { background: #4338CA; color: white; }
    .stDownloadButton button {
        background: white; color: #4F46E5; border: 1px solid #D6DAE8; border-radius: 9px; font-weight: 600;
    }

    /* Tableaux */
    [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #E8EBF2; }

    /* Onglets et selecteurs plus doux */
    .stSelectbox label, .stSlider label, .stTextInput label {
        font-size: 12px !important; color: #5A6A84 !important; font-weight: 600 !important;
    }
    </style>
""", unsafe_allow_html=True)


def bandeau_retenir(texte):
    """Affiche un bandeau premium 'À retenir' avec accent indigo."""
    st.markdown(f'''
    <div style="margin:16px 0; padding:15px 18px; border-radius:12px;
        background:linear-gradient(90deg, rgba(79,70,229,0.07), rgba(79,70,229,0.02));
        border:1px solid rgba(79,70,229,0.15); display:flex; align-items:center; gap:12px;">
      <span style="color:#4F46E5; font-size:18px;">\u25c6</span>
      <span style="font-size:12.5px; color:#3A4A66; line-height:1.45;">{texte}</span>
    </div>''', unsafe_allow_html=True)


def sous_titre_page(texte):
    """Petit sous-titre gris sous le titre de page."""
    st.markdown(f'<div style="font-size:13px; color:#7A889E; margin:-8px 0 4px;">{texte}</div>', unsafe_allow_html=True)


@st.cache_data
def charger():
    df = ctrl.charger_donnees("wandercraft_finance_v2.csv")
    rapport = ctrl.executer_controles(df)
    detail = ctrl.detail_anomalies(df)
    return df, rapport, detail

@st.cache_data
def charger_rapprochement():
    df = ctrl.charger_donnees("wandercraft_finance_v2.csv")
    releve = rap.charger_releve("releve_bancaire_v2.csv")
    rappro, suspens = rap.rapprocher(df, releve)
    synth = rap.synthese_rapprochement(rappro, suspens)
    causes = rap.analyser_non_rapproches(rappro)
    return rappro, suspens, synth, causes

df, rapport, detail = charger()

nb_pieces = len(df)
nb_anomalies = detail["id_piece"].nunique()
taux_anomalie = nb_anomalies / nb_pieces * 100
montant_risque = detail.drop_duplicates("id_piece")["montant_eur"].abs().sum()

# Journal de traitement (audit trail)
journal = audit.charger_journal()
detail_suivi = audit.enrichir_avec_statut(detail, journal)
suivi = audit.synthese_traitement(detail_suivi)

# ---------------------------------------------------------------- Navigation
st.sidebar.markdown("""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0 2px;">
  <div style="width:36px;height:36px;border-radius:9px;background:linear-gradient(135deg,#4F46E5,#6366F1);
       display:flex;align-items:center;justify-content:center;color:white;font-weight:800;font-size:16px;">W</div>
  <div style="color:white;font-size:16px;font-weight:700;">Finance Copilot</div>
</div>
<div style="color:#6B7A96;font-size:11px;padding:2px 0 14px;">Prototype — controle comptable</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigation", [
    "Vue d'ensemble", "Controle des factures", "Rapprochement bancaire",
    "Preparation de cloture", "Relances fournisseurs", "Assistant IA",
    "Journal & tracabilite", "Simulateur de gains",
])
st.sidebar.markdown("---")
st.sidebar.metric("Pieces analysees", f"{nb_pieces:,}".replace(",", " "))
st.sidebar.metric("Anomalies detectees", f"{nb_anomalies:,}".replace(",", " "))
st.sidebar.metric("Deja traitees", f"{suivi['taux_traitement']:.0f} %")
st.sidebar.markdown("---")
st.sidebar.caption("Prototype sur donnees synthetiques. L'outil signale et prepare ; "
                   "la validation reste humaine et tracee.")


# ============================================================= VUE D'ENSEMBLE
if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")
    sous_titre_page("Etat du controle comptable sur la periode — exercice glissant 2023-2025")
    bandeau_retenir(f"<b>A retenir :</b> {nb_anomalies:,} anomalies detectees sur {nb_pieces:,} ecritures "
                    f"({taux_anomalie:.1f} %). Priorite du jour : traiter les factures en double et les "
                    f"ecarts de conversion, soit l'essentiel du montant a risque.".replace(",", " "))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pieces analysees", f"{nb_pieces:,}".replace(",", " "))
    c2.metric("Anomalies detectees", f"{nb_anomalies:,}".replace(",", " "),
              f"{taux_anomalie:.1f} % du volume")
    c3.metric("Montant a fiabiliser", f"{montant_risque/1e6:.1f} M EUR")
    c4.metric("Anomalies traitees", f"{suivi['taux_traitement']:.0f} %")

    st.markdown("###")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="titre-section">Anomalies par type de controle</div>',
                    unsafe_allow_html=True)
        r = rapport[rapport["Pièces signalées"] > 0].sort_values("Pièces signalées")
        fig = px.bar(r, x="Pièces signalées", y="Contrôle", orientation="h",
                     color_discrete_sequence=[BLEU])
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=6, b=0),
                          plot_bgcolor="white", yaxis_title="", xaxis_title="Pieces")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.markdown('<div class="titre-section">Avancement du traitement</div>',
                    unsafe_allow_html=True)
        etat = pd.DataFrame({
            "Statut": ["A traiter", "En cours", "Corrige / Valide", "Faux positif"],
            "Nombre": [suivi.get("À traiter", 0), suivi.get("En cours", 0),
                       suivi.get("Corrigé / Validé", 0), suivi.get("Faux positif", 0)],
        })
        fig2 = px.pie(etat, values="Nombre", names="Statut", hole=0.5,
                      color="Statut", color_discrete_map={
                          "A traiter": "#94A3B8", "En cours": ORANGE,
                          "Corrige / Valide": VERT, "Faux positif": "#CBD5E1"})
        fig2.update_layout(height=380, margin=dict(l=0, r=0, t=6, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="titre-section">Perimetres couverts</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, (t, d) in zip(cols, [("Factures", "10 controles + traitement trace"),
                                  ("Banque", "Rapprochement ~79 % auto"),
                                  ("Cloture", "Cut-off FNP / CCA / CAP"),
                                  ("Fournisseurs", "Relances graduees")]):
        col.markdown(f"**{t}**  \n{d}")

    st.info("Positionnement : ce prototype demontre la faisabilite de l'automatisation "
            "des controles de premier niveau. Les donnees sont synthetiques et calibrees "
            "sur l'ordre de grandeur d'une ETI industrielle (~100 M EUR de charges/an).")


# ======================================================= CONTROLE DES FACTURES
elif page == "Controle des factures":
    st.title("Controle des factures")
    sous_titre_page("Liste de travail et prise en charge tracee des anomalies")
    n_a_traiter = int((detail_suivi["statut_traitement"] == "À traiter").sum())
    bandeau_retenir(f"<b>{n_a_traiter:,} anomalies a traiter.</b> Commencez par les montants les plus eleves ; "
                    f"chaque decision (corrige, faux positif...) est horodatee dans le journal.".replace(",", " "))

    f1, f2, f3, f4 = st.columns(4)
    choix_a = f1.selectbox("Type d'anomalie", ["Toutes"] + sorted(detail_suivi["anomalie"].unique().tolist()))
    choix_f = f2.selectbox("Fournisseur", ["Tous"] + sorted(detail_suivi["fournisseur_ou_employe"].unique().tolist()))
    choix_s = f3.selectbox("Statut de traitement", ["Tous"] + audit.STATUTS)
    recherche = f4.text_input("Rechercher une piece", placeholder="Ex : FAC-123456")

    vue = detail_suivi.copy()
    if choix_a != "Toutes": vue = vue[vue["anomalie"] == choix_a]
    if choix_f != "Tous": vue = vue[vue["fournisseur_ou_employe"] == choix_f]
    if choix_s != "Tous": vue = vue[vue["statut_traitement"] == choix_s]
    if recherche: vue = vue[vue["id_piece"].str.contains(recherche, case=False, na=False)]

    st.markdown(f"**{len(vue):,}** piece(s) — dont "
                f"{(vue['statut_traitement']=='À traiter').sum()} a traiter.".replace(",", " "))

    if len(vue) == 0:
        st.success("Aucune piece ne correspond a ces criteres. "
                   "Si vous venez de tout traiter, felicitations !")
    else:
        colonnes = ["statut_traitement", "anomalie", "id_piece", "type_piece",
                    "fournisseur_ou_employe", "pays", "categorie", "compte", "devise",
                    "montant_ht", "taux_tva", "montant_tva", "montant_ttc",
                    "taux_change", "montant_eur", "date_piece", "date_paiement",
                    "numero_bc", "centre_cout"]
        colonnes = [c for c in colonnes if c in vue.columns]
        st.caption("Astuce : faites defiler le tableau horizontalement pour voir toutes "
                   "les colonnes (montant HT, TVA, taux de change, centre de cout...).")
        st.dataframe(vue[colonnes].head(300), use_container_width=True, hide_index=True, height=360)

        st.markdown('<div class="titre-section">Prendre en charge une anomalie</div>',
                    unsafe_allow_html=True)
        st.caption("Selectionnez une piece, qualifiez-la et tracez votre decision. "
                   "Chaque action est horodatee dans le journal.")
        d1, d2, d3 = st.columns([2, 2, 3])
        piece_sel = d1.selectbox("Piece", vue["id_piece"].unique().tolist())
        ligne_sel = vue[vue["id_piece"] == piece_sel].iloc[0]
        anomalie_sel = ligne_sel["anomalie"]
        d1.caption(f"Anomalie : {anomalie_sel}")
        nouveau_statut = d2.selectbox("Nouveau statut", audit.STATUTS)
        utilisateur = d2.text_input("Votre identifiant", value="m.kamga")
        commentaire = d3.text_area("Commentaire (motif, action)", height=90,
                                   placeholder="Ex : verifie dans l'ERP, facture unique -> faux positif")
        if d3.button("Enregistrer la decision", type="primary"):
            audit.enregistrer_decision(piece_sel, anomalie_sel, nouveau_statut, utilisateur, commentaire)
            st.success(f"Decision enregistree : {piece_sel} -> {nouveau_statut}. "
                       "Rechargez la page pour voir le statut mis a jour.")

        csv = vue[colonnes].to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("Exporter la selection (CSV)", csv, "anomalies.csv", "text/csv")


# ===================================================== RAPPROCHEMENT BANCAIRE
elif page == "Rapprochement bancaire":
    st.title("Rapprochement bancaire")
    sous_titre_page("Lettrage automatique des reglements : releve bancaire vs factures fournisseurs")
    with st.spinner("Rapprochement en cours..."):
        rappro, suspens, synth, causes = charger_rapprochement()
    bandeau_retenir(f"<b>{synth['taux_rapprochement']:.1f} % rapproches automatiquement.</b> Les "
                    f"{synth['non_rapproches']:,} mouvements restants ne sont pas des erreurs : ce sont des "
                    f"cas metier (libelles divergents, paiements groupes) a traiter en revue assistee.".replace(",", " "))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mouvements", f"{synth['mouvements_total']:,}".replace(",", " "))
    c2.metric("Rapproches auto", f"{synth['taux_rapprochement']:.1f} %")
    c3.metric("Avec ecarts a valider", f"{synth['taux_auto_global']:.1f} %")
    c4.metric("A revoir manuellement", f"{synth['non_rapproches']:,}".replace(",", " "))

    st.markdown("###")
    g1, g2 = st.columns([1, 1])
    with g1:
        st.markdown('<div class="titre-section">Statut des mouvements</div>', unsafe_allow_html=True)
        stat = rappro["statut"].value_counts().reset_index()
        stat.columns = ["Statut", "Nombre"]
        fig = px.pie(stat, values="Nombre", names="Statut", hole=0.5, color="Statut",
                     color_discrete_map={"Rapproche": VERT, "Ecart de montant": ORANGE,
                                         "Non rapproche": "#94A3B8"})
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=6, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.markdown('<div class="titre-section">Pourquoi certains ne matchent pas</div>',
                    unsafe_allow_html=True)
        st.caption("Un non-rapprochement n'est pas une erreur : c'est souvent un cas "
                   "metier a traiter manuellement.")
        st.dataframe(causes, use_container_width=True, hide_index=True)
        st.metric("Factures sans reglement identifie", f"{synth['factures_en_suspens']:,}".replace(",", " "),
                  f"{synth['montant_en_suspens']/1e6:.1f} M EUR")

    st.markdown('<div class="titre-section">Detail des mouvements</div>', unsafe_allow_html=True)
    fstatut = st.selectbox("Filtrer par statut", ["Ecart de montant", "Non rapproche", "Rapproche"])
    st.dataframe(rappro[rappro["statut"] == fstatut].head(400),
                 use_container_width=True, hide_index=True, height=360)
    csv = rappro.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button("Exporter le rapprochement (CSV)", csv, "rapprochement.csv", "text/csv")


# ======================================================= PREPARATION CLOTURE
elif page == "Preparation de cloture":
    st.title("Preparation de cloture (cut-off)")
    sous_titre_page("Ecritures de regularisation a soumettre au comptable senior")
    bandeau_retenir("<b>L'outil propose, le senior valide.</b> Le cut-off rattache chaque charge au bon "
                    "exercice via trois types d'ecritures : factures non parvenues (FNP), charges constatees "
                    "d'avance (CCA) et charges a payer (CAP).")

    date_c = st.selectbox("Date de cloture", ["2024-12-31", "2024-09-30", "2024-06-30", "2023-12-31"])
    cutoff = clo.preparer_cutoff(df, date_c)
    sc = clo.synthese_cloture(cutoff)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ecritures proposees", f"{sc['total']:,}".replace(",", " "))
    c2.metric("FNP", f"{sc['fnp']:,}".replace(",", " "))
    c3.metric("CCA", f"{sc['cca']:,}".replace(",", " "))
    c4.metric("CAP", f"{sc['cap']:,}".replace(",", " "))

    st.markdown("###")
    g1, g2 = st.columns([1, 1])
    with g1:
        st.markdown('<div class="titre-section">Montants par type</div>', unsafe_allow_html=True)
        rep = pd.DataFrame({"Type": ["FNP", "CCA", "CAP"],
                            "Montant": [sc.get("montant_fnp", 0), sc.get("montant_cca", 0), sc.get("montant_cap", 0)]})
        fig = px.bar(rep, x="Type", y="Montant", color="Type",
                     color_discrete_sequence=[BLEU, ORANGE, VERT], text_auto=".2s")
        fig.update_layout(height=340, showlegend=False, plot_bgcolor="white",
                          margin=dict(l=0, r=0, t=6, b=0), yaxis_title="EUR")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.markdown('<div class="titre-section">Synthese a regulariser</div>', unsafe_allow_html=True)
        st.metric("Total a regulariser", f"{sc['montant_total']/1e6:.1f} M EUR")
        st.write(f"- **FNP** : {sc.get('montant_fnp',0)/1e6:.1f} M EUR a provisionner")
        st.write(f"- **CCA** : {sc.get('montant_cca',0)/1e6:.1f} M EUR a reporter")
        st.write(f"- **CAP** : {sc.get('montant_cap',0)/1e6:.1f} M EUR a constater")
        st.caption("Note : estimations de premier niveau, a affiner avec les receptions "
                   "et les contrats. Certaines pieces peuvent relever de plusieurs categories.")

    st.markdown('<div class="titre-section">Detail des ecritures proposees</div>', unsafe_allow_html=True)
    tc = st.selectbox("Filtrer par type", ["Tous", "FNP", "CCA", "CAP"])
    vue = cutoff if tc == "Tous" else cutoff[cutoff["type_ecriture"] == tc]
    st.dataframe(vue, use_container_width=True, hide_index=True, height=340)
    csv = cutoff.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button("Exporter les ecritures (CSV)", csv, "cutoff.csv", "text/csv")


# ======================================================= RELANCES FOURNISSEURS
elif page == "Relances fournisseurs":
    st.title("Relances fournisseurs")
    sous_titre_page("Pieces manquantes et relances graduees selon l'anciennete")
    bandeau_retenir("<b>L'outil prepare les brouillons d'email ; l'envoi reste declenche par un humain.</b> "
                    "Les pieces a reclamer sont detectees et les relances graduees selon leur anciennete "
                    "(simple, ferme, escalade).")

    date_r = st.selectbox("Date de reference", ["2025-06-30", "2025-03-31", "2024-12-31"])
    relances = rel.preparer_relances(df, date_r)
    sr = rel.synthese_relances(relances)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Relances a traiter", f"{sr.get('total',0):,}".replace(",", " "))
    c2.metric("Niveau 1", f"{sr.get('niveau_1',0):,}".replace(",", " "))
    c3.metric("Niveau 2", f"{sr.get('niveau_2',0):,}".replace(",", " "))
    c4.metric("Niveau 3 (escalade)", f"{sr.get('niveau_3',0):,}".replace(",", " "))

    st.markdown("###")
    st.markdown('<div class="titre-section">Relances a effectuer</div>', unsafe_allow_html=True)
    if len(relances) == 0:
        st.success("Aucune relance a effectuer a cette date.")
    else:
        st.dataframe(relances, use_container_width=True, hide_index=True, height=320)
        st.markdown('<div class="titre-section">Brouillon d\'email</div>', unsafe_allow_html=True)
        fourn = st.selectbox("Fournisseur", relances["fournisseur"].unique().tolist())
        lf = relances[relances["fournisseur"] == fourn]
        email = rel.generer_email_relance(fourn, list(zip(lf["id_piece"], lf["motif"])), lf.iloc[0]["niveau"])
        st.text_area("A valider avant envoi", email, height=300)


# ================================================================= ASSISTANT IA
elif page == "Assistant IA":
    st.title("Assistant IA")
    sous_titre_page("Interrogez les resultats de controle en langage naturel")
    bandeau_retenir("<b>L'IA analyse et redige — elle ne calcule jamais.</b> Les chiffres proviennent du "
                    "moteur deterministe ; l'assistant s'appuie uniquement sur des donnees agregees pour "
                    "vous aider a lire et prioriser.")
    st.markdown("**Exemples :** _Quelles anomalies sont les plus couteuses ? / Quel fournisseur "
                "concentre le plus d'ecarts ? / Par quoi commencer ?_")

    question = st.text_input("Votre question :", placeholder="Ex : par quelles anomalies commencer ?")

    def contexte():
        resume = rapport.to_string(index=False)
        top = (detail.groupby("anomalie").agg(nombre=("id_piece", "nunique"),
               montant=("montant_eur", lambda x: round(x.abs().sum(), 2))).to_string())
        return f"Rapport de controle :\n{resume}\n\nAnomalies par type :\n{top}"

    if question:
        try:
            import google.generativeai as genai
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel("models/gemini-flash-latest")
            prompt = ("Tu es un assistant comptable. Reponds en francais, precis et concis "
                      "(3-5 phrases), uniquement a partir des donnees ci-dessous. N'invente aucun "
                      f"chiffre.\n\n=== DONNEES ===\n{contexte()}\n\n=== QUESTION ===\n{question}")
            with st.spinner("Analyse en cours..."):
                st.success(model.generate_content(prompt).text)
        except Exception:
            st.warning("Assistant IA indisponible (cle API ou quota). Analyse automatique :")
            top = (detail.groupby("anomalie").agg(nb=("id_piece", "nunique"),
                   montant=("montant_eur", lambda x: round(x.abs().sum(), 2)))
                   .sort_values("montant", ascending=False))
            st.dataframe(top, use_container_width=True)


# ============================================================ JOURNAL & TRACABILITE
elif page == "Journal & tracabilite":
    st.title("Journal & tracabilite")
    sous_titre_page("Historique horodate et non modifiable des decisions — audit trail")
    bandeau_retenir("<b>Chaque decision est tracee : qui, quoi, quand, pourquoi.</b> C'est la base de la "
                    "tracabilite exigee en comptabilite et la memoire des traitements de l'equipe.")

    if len(journal) == 0:
        st.warning("Le journal est vide pour l'instant. Rendez-vous dans 'Controle des "
                   "factures' pour prendre en charge une anomalie : votre decision "
                   "apparaitra ici.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Decisions enregistrees", len(journal))
        c2.metric("Pieces traitees", journal["id_piece"].nunique())
        c3.metric("Intervenants", journal["utilisateur"].nunique())
        st.markdown('<div class="titre-section">Journal des decisions</div>', unsafe_allow_html=True)
        jaff = journal.sort_values("horodatage", ascending=False).copy()
        jaff["horodatage"] = jaff["horodatage"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(jaff, use_container_width=True, hide_index=True, height=380)
        csv = journal.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button("Exporter le journal (CSV)", csv, "journal_traitement.csv", "text/csv")


# ============================================================ SIMULATEUR DE GAINS
elif page == "Simulateur de gains":
    st.title("Simulateur de gains")
    sous_titre_page("Estimation prudente du temps redeploye vers l'analyse")
    bandeau_retenir("<b>Hypothese realiste :</b> aujourd'hui les controles se font surtout par sondage. "
                    "L'automatisation etend la couverture et redeploie du temps vers l'analyse, plutot que "
                    "de remplacer un controle manuel exhaustif.")
    st.caption("Hypothese realiste : aujourd'hui, les controles se font surtout par sondage. "
               "L'automatisation ne remplace pas un controle exhaustif manuel (impraticable) ; "
               "elle etend la couverture et redeploie du temps de saisie/verification vers "
               "l'analyse. On chiffre ici le temps de revue des seules anomalies detectees.")

    c1, c2 = st.columns(2)
    with c1:
        temps = st.slider("Temps de revue manuelle par anomalie (minutes)", 2, 30, 8)
        cout = st.slider("Cout horaire charge (EUR)", 20, 80, 40)
    with c2:
        part_auto = st.slider("Part des anomalies pre-qualifiees par l'outil (%)", 30, 90, 60)
        freq = st.selectbox("Frequence", ["Mensuelle", "Trimestrielle", "Annuelle"])
    mult = {"Mensuelle": 12, "Trimestrielle": 4, "Annuelle": 1}[freq]

    # Temps economise = anomalies pre-qualifiees x temps de revue evite
    anomalies_traitables = nb_anomalies * part_auto / 100
    heures_economisees = anomalies_traitables * temps / 60
    cout_economise = heures_economisees * cout * mult
    heures_an = heures_economisees * mult

    st.markdown("###")
    r1, r2, r3 = st.columns(3)
    r1.metric("Anomalies pre-qualifiees", f"{anomalies_traitables:,.0f}".replace(",", " "))
    r2.metric("Heures redeployees / an", f"{heures_an:,.0f} h".replace(",", " "))
    r3.metric("Valeur annuelle estimee", f"{cout_economise:,.0f} EUR".replace(",", " "))

    st.success(f"En pre-qualifiant automatiquement {part_auto} % des {nb_anomalies:,} anomalies, "
               f"l'outil permettrait de redeployer environ **{heures_an:,.0f} heures par an** "
               f"vers des taches a plus forte valeur, soit une valeur estimee de "
               f"**{cout_economise:,.0f} EUR** ({freq.lower()}).".replace(",", " "))
    st.caption("Estimation indicative, a affiner avec les temps reels de l'equipe. "
               "Le gain principal est qualitatif : couverture etendue et tracabilite, "
               "au-dela du temps economise.")
