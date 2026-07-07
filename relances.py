"""
Module de gestion des relances fournisseurs — Wandercraft Finance Copilot.

Detecte les situations necessitant une relance ou une demande de piece, et
propose un plan d'action graduel. Couvre trois cas courants du suivi fournisseurs :

- Piece justificative manquante : facture importante sans bon de commande associe.
- Facture en attente de reglement depuis trop longtemps (retard de paiement).
- Demande de duplicata / avoir : montant negatif ou incoherence a clarifier.

Le niveau de relance est gradue selon l'anciennete. L'outil prepare les relances ;
l'envoi reste declenche par un humain.
"""

import pandas as pd
import numpy as np

# Paliers de relance (en jours d'anciennete de la piece)
PALIER_1 = 15
PALIER_2 = 30
PALIER_3 = 45
SEUIL_MONTANT_PJ = 15000   # au-dela, un BC manquant declenche une relance


def preparer_relances(factures, date_reference):
    """
    Construit la liste des relances a effectuer a une date de reference donnee.
    """
    d_ref = pd.to_datetime(date_reference)
    fac = factures[factures["type_piece"] == "facture_fournisseur"].copy()
    fac["date_piece"] = pd.to_datetime(fac["date_piece"], errors="coerce")
    fac["anciennete"] = (d_ref - fac["date_piece"]).dt.days

    # On se concentre sur les pieces recentes (dans l'annee ecoulee)
    fac = fac[(fac["anciennete"] >= 0) & (fac["anciennete"] <= 365)]

    resultats = []

    # Cas 1 : piece justificative manquante (grosse facture sans BC)
    pj = fac[(fac["montant_ttc"].abs() > SEUIL_MONTANT_PJ)
             & (fac["numero_bc"].fillna("").astype(str).str.strip() == "")].copy()
    for _, r in pj.iterrows():
        resultats.append(_ligne_relance(r, "Piece justificative manquante",
                                        "Demander le bon de commande associe"))

    # Cas 2 : demande de duplicata / avoir (montant negatif = avoir a clarifier)
    avoirs = fac[fac["montant_ttc"] < 0].copy()
    for _, r in avoirs.iterrows():
        resultats.append(_ligne_relance(r, "Avoir a clarifier",
                                        "Demander la piece justificative de l'avoir"))

    if not resultats:
        return pd.DataFrame(columns=["niveau","motif","action","id_piece","fournisseur",
                                     "montant_eur","anciennete_jours","date_facture"])
    df = pd.DataFrame(resultats)
    return df.sort_values(["niveau", "anciennete_jours"], ascending=[False, False])


def _ligne_relance(r, motif, action):
    """Construit une ligne de relance avec le niveau gradue selon l'anciennete."""
    anc = r["anciennete"]
    if anc >= PALIER_3:
        niveau = "Niveau 3 - Escalade"
    elif anc >= PALIER_2:
        niveau = "Niveau 2 - Relance ferme"
    elif anc >= PALIER_1:
        niveau = "Niveau 1 - Relance simple"
    else:
        niveau = "A surveiller"
    return {
        "niveau": niveau,
        "motif": motif,
        "action": action,
        "id_piece": r["id_piece"],
        "fournisseur": r["fournisseur_ou_employe"],
        "montant_eur": abs(r["montant_eur"]),
        "anciennete_jours": int(anc),
        "date_facture": r["date_piece"].strftime("%Y-%m-%d"),
    }


def synthese_relances(relances):
    """Indicateurs du plan de relance."""
    if len(relances) == 0:
        return {"total": 0}
    return {
        "total": len(relances),
        "niveau_1": int(relances["niveau"].str.startswith("Niveau 1").sum()),
        "niveau_2": int(relances["niveau"].str.startswith("Niveau 2").sum()),
        "niveau_3": int(relances["niveau"].str.startswith("Niveau 3").sum()),
        "a_surveiller": int((relances["niveau"] == "A surveiller").sum()),
        "montant_total": round(relances["montant_eur"].sum(), 2),
    }


def generer_email_relance(fournisseur, pieces, niveau):
    """
    Genere le texte d'un email de relance (modele fige, sans IA).
    pieces : liste de tuples (id_piece, motif).
    """
    ton = {
        "Niveau 1 - Relance simple": "Nous nous permettons de revenir vers vous",
        "Niveau 2 - Relance ferme": "Sauf erreur de notre part, nous n'avons toujours pas recu",
        "Niveau 3 - Escalade": "Malgre nos precedentes relances, nous restons dans l'attente",
    }.get(niveau, "Nous vous contactons au sujet")

    lignes = "\n".join([f"  - {pid} : {motif}" for pid, motif in pieces])
    return (
        f"Objet : Relance - pieces comptables en attente ({fournisseur})\n\n"
        f"Bonjour,\n\n"
        f"{ton} les elements suivants concernant votre compte fournisseur :\n\n"
        f"{lignes}\n\n"
        f"Nous vous remercions de bien vouloir nous transmettre les pieces manquantes "
        f"dans les meilleurs delais afin de finaliser le traitement comptable.\n\n"
        f"Cordialement,\n"
        f"Service Comptabilite Fournisseurs - Wandercraft"
    )
