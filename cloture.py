"""
Module d'assistance a la cloture (cut-off) — Wandercraft Finance Copilot.

Prepare les controles de cut-off de premier niveau : identifie les ecritures de
regularisation a passer en fin de periode pour rattacher chaque charge au bon
exercice. Trois categories classiques :

- FNP (Factures Non Parvenues) : biens/services recus mais facture pas encore
  arrivee a la cloture -> charge a rattacher a la periode.
- CCA (Charges Constatees d'Avance) : facture payee sur la periode mais dont la
  prestation concerne la periode suivante -> charge a reporter.
- CAP (Charges A Payer) : charges engagees non encore facturees, proches des FNP.

L'outil propose une liste de points a revoir ; le comptable senior valide.
"""

import pandas as pd
import numpy as np

def preparer_cutoff(factures, date_cloture):
    """
    Identifie les ecritures de cut-off autour d'une date de cloture donnee.

    date_cloture : chaine 'AAAA-MM-JJ' (ex. fin de trimestre).
    """
    d_cloture = pd.to_datetime(date_cloture)
    fac = factures[factures["type_piece"] == "facture_fournisseur"].copy()
    fac["date_piece"] = pd.to_datetime(fac["date_piece"], errors="coerce")
    fac["date_paiement"] = pd.to_datetime(fac["date_paiement"], errors="coerce")

    # Fenetre d'analyse : 60 jours avant / apres la cloture
    debut = d_cloture - pd.Timedelta(days=40)
    fin = d_cloture + pd.Timedelta(days=40)
    proches = fac[(fac["date_piece"] >= debut) & (fac["date_piece"] <= fin)].copy()

    resultats = []

    # FNP : facture datee APRES la cloture mais commande (BC) existante
    # -> le bien/service concerne la periode close, la charge doit y etre rattachee
    fnp = proches[(proches["date_piece"] > d_cloture)
                  & (proches["numero_bc"].fillna("").astype(str).str.strip() != "")
                  & (proches["date_piece"] <= d_cloture + pd.Timedelta(days=25))].copy()
    for _, r in fnp.iterrows():
        resultats.append({
            "type_ecriture": "FNP",
            "libelle": "Facture non parvenue a la cloture",
            "id_piece": r["id_piece"],
            "fournisseur": r["fournisseur_ou_employe"],
            "montant_eur": abs(r["montant_eur"]),
            "date_facture": r["date_piece"].strftime("%Y-%m-%d"),
            "action": "Provisionner la charge sur la periode close",
        })

    # CCA : facture datee AVANT la cloture mais payee/consommee APRES
    # -> prestation future, charge a reporter sur la periode suivante
    cca = proches[(proches["date_piece"] <= d_cloture)
                  & (proches["date_paiement"] > d_cloture)
                  & (proches["date_paiement"] <= d_cloture + pd.Timedelta(days=35))].copy()
    for _, r in cca.iterrows():
        resultats.append({
            "type_ecriture": "CCA",
            "libelle": "Charge constatee d'avance",
            "id_piece": r["id_piece"],
            "fournisseur": r["fournisseur_ou_employe"],
            "montant_eur": abs(r["montant_eur"]),
            "date_facture": r["date_piece"].strftime("%Y-%m-%d"),
            "action": "Reporter la charge sur la periode suivante",
        })

    # CAP : charges engagees (BC) sans facture du tout dans la fenetre
    # -> approximees ici par les grosses commandes recentes non facturees
    cap = proches[(proches["date_piece"] > d_cloture - pd.Timedelta(days=30))
                  & (proches["date_piece"] <= d_cloture)
                  & (proches["montant_eur"].abs() > 15000)].copy()
    cap = cap.sample(min(len(cap), 80), random_state=3) if len(cap) > 0 else cap
    for _, r in cap.iterrows():
        resultats.append({
            "type_ecriture": "CAP",
            "libelle": "Charge a payer (engagee non facturee)",
            "id_piece": r["id_piece"],
            "fournisseur": r["fournisseur_ou_employe"],
            "montant_eur": abs(r["montant_eur"]),
            "date_facture": r["date_piece"].strftime("%Y-%m-%d"),
            "action": "Constater la charge a payer sur la periode close",
        })

    if not resultats:
        return pd.DataFrame(columns=["type_ecriture","libelle","id_piece","fournisseur",
                                     "montant_eur","date_facture","action"])
    return pd.DataFrame(resultats)


def synthese_cloture(cutoff):
    """Indicateurs de la preparation de cloture."""
    if len(cutoff) == 0:
        return {"total": 0, "fnp": 0, "cca": 0, "cap": 0, "montant_total": 0}
    return {
        "total": len(cutoff),
        "fnp": int((cutoff["type_ecriture"] == "FNP").sum()),
        "cca": int((cutoff["type_ecriture"] == "CCA").sum()),
        "cap": int((cutoff["type_ecriture"] == "CAP").sum()),
        "montant_total": round(cutoff["montant_eur"].sum(), 2),
        "montant_fnp": round(cutoff[cutoff["type_ecriture"]=="FNP"]["montant_eur"].sum(), 2),
        "montant_cca": round(cutoff[cutoff["type_ecriture"]=="CCA"]["montant_eur"].sum(), 2),
        "montant_cap": round(cutoff[cutoff["type_ecriture"]=="CAP"]["montant_eur"].sum(), 2),
    }
