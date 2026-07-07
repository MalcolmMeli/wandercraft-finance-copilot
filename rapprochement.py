"""
Module de rapprochement bancaire — Finance Copilot V2.

Rapproche les mouvements du releve bancaire avec les factures fournisseurs.
Version 2 : rapprochement plus exigeant et plus realiste. Un mouvement n'est
rapproche automatiquement que si le beneficiaire ET le montant correspondent.
Les cas frequents en pratique (libelle bancaire divergent, paiement groupe,
escompte) ne matchent pas au premier passage et sont orientes vers une revue
manuelle assistee, avec leur cause probable. Cela reflete la realite d'un
rapprochement (typiquement 70-80 % d'automatisation au premier passage).

L'outil propose ; le comptable valide et traite les cas restants.
"""

import pandas as pd
import numpy as np

TOLERANCE_MONTANT = 0.01
SEUIL_ECART = 0.03   # escompte/arrondi tolere pour un "ecart de montant"


def charger_releve(chemin):
    rel = pd.read_csv(chemin, sep=";")
    rel["date_mouvement"] = pd.to_datetime(rel["date_mouvement"], errors="coerce")
    return rel


def _libelle_exploitable(libelle):
    """
    Determine si le libelle bancaire permet d'identifier le fournisseur.
    Un libelle 'VIR <Nom complet>' est exploitable ; un libelle tronque,
    'PRLV', 'VIR SEPA', 'GROUPE' ou un frais bancaire ne l'est pas
    directement et demande une revue manuelle.
    """
    lib = str(libelle).strip()
    if lib.upper().startswith("VIR ") and "SEPA" not in lib.upper():
        return lib[4:].strip()   # nom du fournisseur suppose
    return None


def rapprocher(factures, releve):
    paiements = releve[releve["montant"] < 0].copy()
    paiements["montant_abs"] = paiements["montant"].abs().round(2)
    paiements["fournisseur_identifie"] = paiements["libelle"].apply(_libelle_exploitable)

    fac = factures[(factures["type_piece"] == "facture_fournisseur")
                   & (factures["montant_ttc"] > 0)].copy()
    fac["montant_ttc"] = fac["montant_ttc"].round(2)

    morceaux = []
    factures_utilisees = set()

    # 1. Mouvements dont le fournisseur est identifiable -> tentative de match
    identifiables = paiements[paiements["fournisseur_identifie"].notna()]
    for fournisseur, pmts in identifiables.groupby("fournisseur_identifie"):
        candidates = fac[fac["fournisseur_ou_employe"] == fournisseur]
        if len(candidates) == 0:
            bloc = pmts.copy()
            bloc["statut"] = "Non rapproche"; bloc["facture_rapprochee"] = ""
            bloc["ecart_montant"] = np.nan; morceaux.append(bloc)
            continue
        cand = candidates.sort_values("montant_ttc")
        pmts_tries = pmts.sort_values("montant_abs")
        app = pd.merge_asof(pmts_tries, cand[["montant_ttc", "id_piece"]],
                            left_on="montant_abs", right_on="montant_ttc", direction="nearest")
        app["ecart"] = (app["montant_abs"] - app["montant_ttc"]).abs()
        cond_exact = app["ecart"] <= TOLERANCE_MONTANT
        cond_proche = app["ecart"] <= app["montant_abs"] * SEUIL_ECART
        app["statut"] = np.where(cond_exact, "Rapproche",
                        np.where(cond_proche, "Ecart de montant", "Non rapproche"))
        app["facture_rapprochee"] = np.where(app["statut"] != "Non rapproche", app["id_piece"], "")
        app["ecart_montant"] = np.where(app["statut"] == "Ecart de montant", app["ecart"].round(2), np.nan)
        for pid in app.loc[app["statut"] != "Non rapproche", "id_piece"]:
            factures_utilisees.add(pid)
        morceaux.append(app)

    # 2. Mouvements non identifiables -> non rapproches, avec cause
    non_ident = paiements[paiements["fournisseur_identifie"].isna()].copy()
    non_ident["statut"] = "Non rapproche"
    non_ident["facture_rapprochee"] = ""
    non_ident["ecart_montant"] = np.nan
    morceaux.append(non_ident)

    rappro = pd.concat(morceaux, ignore_index=True)
    # On supprime la colonne 'montant' d'origine (montant signe du releve) pour eviter
    # un doublon avec 'montant_abs' que l'on renomme ensuite en 'montant'.
    if "montant" in rappro.columns:
        rappro = rappro.drop(columns=["montant"])
    rappro = rappro.rename(columns={"montant_abs": "montant"})
    cols = ["id_mouvement", "date_mouvement", "libelle", "beneficiaire", "montant",
            "statut", "facture_rapprochee", "ecart_montant"]
    for c in cols:
        if c not in rappro.columns:
            rappro[c] = np.nan
    rappro = rappro[cols]

    factures_en_suspens = fac[~fac["id_piece"].isin(factures_utilisees)][
        ["id_piece", "fournisseur_ou_employe", "montant_ttc", "devise", "date_piece", "date_paiement"]
    ].copy()
    return rappro, factures_en_suspens


def synthese_rapprochement(rappro, factures_en_suspens):
    total = len(rappro)
    n_r = (rappro["statut"] == "Rapproche").sum()
    n_e = (rappro["statut"] == "Ecart de montant").sum()
    n_n = (rappro["statut"] == "Non rapproche").sum()
    return {
        "mouvements_total": total,
        "rapproches": int(n_r),
        "ecarts": int(n_e),
        "non_rapproches": int(n_n),
        "taux_rapprochement": round(n_r / total * 100, 1) if total else 0,
        "taux_auto_global": round((n_r + n_e) / total * 100, 1) if total else 0,
        "factures_en_suspens": len(factures_en_suspens),
        "montant_en_suspens": round(factures_en_suspens["montant_ttc"].abs().sum(), 2),
    }


def analyser_non_rapproches(rappro):
    """Classe les mouvements non rapproches par cause probable (aide a la revue)."""
    non = rappro[rappro["statut"] == "Non rapproche"].copy()
    if len(non) == 0:
        return pd.DataFrame(columns=["Cause probable", "Nombre"])

    def cause(row):
        lib = str(row.get("libelle", "")).upper()
        benef = str(row.get("beneficiaire", "")).strip()
        if benef == "" or benef == "nan":
            return "Mouvement sans facture (frais, taxes, virements internes)"
        if "GROUPE" in lib:
            return "Paiement groupe (plusieurs factures en un virement)"
        if "SEPA" in lib or "PRLV" in lib:
            return "Libelle bancaire divergent (a rapprocher manuellement)"
        return "Autre cas a examiner"

    non["cause"] = non.apply(cause, axis=1)
    r = non["cause"].value_counts().reset_index()
    r.columns = ["Cause probable", "Nombre"]
    return r
