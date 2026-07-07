"""
Moteur de contrôles comptables automatisés — Wandercraft Finance Copilot.

Ce module contient toute la logique métier (chargement des données et règles de
contrôle), séparée de l'interface graphique. Chaque contrôle applique une règle
comptable et renvoie les pièces à réviser, sans jamais modifier les données :
l'outil signale, l'humain valide.
"""

import pandas as pd
import numpy as np

# --- Paramètres de contrôle (regroupés pour être ajustables facilement) ---
TAUX_TVA_LEGAUX = [0.0, 0.055, 0.10, 0.20]
TAUX_CHANGE_ATTENDUS = {"EUR": 1.0, "USD": 0.92, "CHF": 1.04, "GBP": 1.17}
PLAFOND_NOTE_DE_FRAIS = 3000        # seuil de la politique de frais (EUR)
SEUIL_GROSSE_FACTURE = 15000        # seuil abaisse, coherent avec les montants ETI        # au-delà, un bon de commande est requis


def charger_donnees(chemin):
    """Charge le fichier comptable et prépare les colonnes de dates."""
    df = pd.read_csv(chemin, sep=";")
    df["date_piece"] = pd.to_datetime(df["date_piece"], errors="coerce")
    df["date_paiement"] = pd.to_datetime(df["date_paiement"], errors="coerce")
    df["mois"] = df["date_piece"].dt.to_period("M").astype(str)
    return df


def _fac_et_ndf(df):
    """Masque des pièces concernées par la TVA (factures et notes de frais)."""
    return df["type_piece"].isin(["facture_fournisseur", "note_de_frais"])


# --- Les dix contrôles. Chacun renvoie (libellé, pièces signalées). ---

def ctrl_ttc(df, tol=0.01):
    """Le total TTC doit être égal au HT plus la TVA."""
    m = _fac_et_ndf(df) & (
        (df["montant_ht"].fillna(0) + df["montant_tva"].fillna(0) - df["montant_ttc"]).abs() > tol
    )
    return "TTC = HT + TVA", df[m]


def ctrl_tva_legale(df):
    """Le taux de TVA doit être un taux légal français."""
    m = _fac_et_ndf(df) & df["taux_tva"].notna() & ~df["taux_tva"].round(3).isin(
        [round(t, 3) for t in TAUX_TVA_LEGAUX]
    )
    return "Taux de TVA conforme", df[m]


def ctrl_ht_manquant(df):
    """Une facture ou note de frais doit avoir un montant HT."""
    m = _fac_et_ndf(df) & df["montant_ht"].isna()
    return "Montant HT présent", df[m]


def ctrl_negatif(df):
    """Aucun montant ne doit être négatif (hors avoir)."""
    m = df["montant_ttc"] < 0
    return "Aucun montant négatif", df[m]


def ctrl_chronologie(df):
    """Un paiement ne peut pas précéder la date de la pièce."""
    m = df["date_paiement"] < df["date_piece"]
    return "Paiement après la facture", df[m]


def ctrl_change(df):
    """Le taux de change doit correspondre à la devise."""
    attendu = df["devise"].map(TAUX_CHANGE_ATTENDUS)
    m = (df["taux_change"] - attendu).abs() > 0.001
    return "Taux de change cohérent", df[m]


def ctrl_conversion(df, tol=0.5):
    """La conversion en euros doit être exacte."""
    m = (df["montant_ttc"] * df["taux_change"] - df["montant_eur"]).abs() > tol
    return "Conversion euro exacte", df[m]


def ctrl_plafond_frais(df):
    """Les notes de frais au-dessus du plafond doivent être revues."""
    m = (df["type_piece"] == "note_de_frais") & (df["montant_ht"] > PLAFOND_NOTE_DE_FRAIS)
    return "Note de frais sous plafond", df[m]


def ctrl_bon_commande(df):
    """Une facture importante doit avoir un bon de commande."""
    m = (
        (df["type_piece"] == "facture_fournisseur")
        & (df["montant_ttc"].abs() > SEUIL_GROSSE_FACTURE)
        & (df["numero_bc"].fillna("").astype(str).str.strip() == "")
    )
    return "Bon de commande présent (grosse facture)", df[m]


def ctrl_doublons(df):
    """Deux factures identiques (fournisseur + montant + devise) sont suspectes."""
    fac = df[df["type_piece"] == "facture_fournisseur"]
    m = fac.duplicated(subset=["fournisseur_ou_employe", "montant_ttc", "devise"], keep=False)
    return "Aucune facture en double", fac[m]


CONTROLES = [
    ctrl_ttc, ctrl_tva_legale, ctrl_ht_manquant, ctrl_negatif, ctrl_chronologie,
    ctrl_change, ctrl_conversion, ctrl_plafond_frais, ctrl_bon_commande, ctrl_doublons,
]


def executer_controles(df):
    """Lance tous les contrôles et renvoie le rapport de synthèse."""
    lignes = []
    for controle in CONTROLES:
        libelle, signalees = controle(df)
        lignes.append({
            "Contrôle": libelle,
            "Statut": "OK" if len(signalees) == 0 else "À revoir",
            "Pièces signalées": len(signalees),
            "Montant concerné (€)": round(signalees["montant_eur"].abs().sum(), 2),
        })
    return pd.DataFrame(lignes)


def detail_anomalies(df):
    """Renvoie toutes les pièces signalées, avec le contrôle qui a échoué."""
    morceaux = []
    for controle in CONTROLES:
        libelle, signalees = controle(df)
        if len(signalees) > 0:
            bloc = signalees.copy()
            bloc.insert(0, "anomalie", libelle)
            morceaux.append(bloc)
    if not morceaux:
        return pd.DataFrame()
    return pd.concat(morceaux, ignore_index=True)
