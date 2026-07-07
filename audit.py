"""
Module de tracabilite et de traitement des anomalies — Finance Copilot V2.

Gere le cycle de vie de chaque anomalie detectee : statut de traitement, decision
humaine, et journal horodate (audit trail). C'est ce qui distingue un outil de
detection d'un outil de gestion : chaque anomalie peut etre prise en charge,
qualifiee (reelle ou faux positif) et tracee.

La persistance se fait dans un fichier local (journal_traitement.csv) afin que les
decisions survivent d'une session a l'autre. En production, ce serait une base de
donnees avec authentification par utilisateur.
"""

import pandas as pd
import os
from datetime import datetime

JOURNAL = "journal_traitement.csv"

STATUTS = ["À traiter", "En cours", "Corrigé / Validé", "Faux positif"]


def _colonnes_journal():
    return ["horodatage", "id_piece", "anomalie", "statut", "utilisateur", "commentaire"]


def charger_journal():
    """Charge le journal de traitement, ou en cree un vide."""
    if os.path.exists(JOURNAL):
        j = pd.read_csv(JOURNAL, sep=";")
        j["horodatage"] = pd.to_datetime(j["horodatage"], errors="coerce")
        return j
    return pd.DataFrame(columns=_colonnes_journal())


def enregistrer_decision(id_piece, anomalie, statut, utilisateur, commentaire=""):
    """Ajoute une decision au journal (append, jamais d'ecrasement : tracabilite)."""
    j = charger_journal()
    ligne = {
        "horodatage": datetime.now(),
        "id_piece": id_piece,
        "anomalie": anomalie,
        "statut": statut,
        "utilisateur": utilisateur,
        "commentaire": commentaire,
    }
    j = pd.concat([j, pd.DataFrame([ligne])], ignore_index=True)
    j.to_csv(JOURNAL, sep=";", index=False)
    return j


def statut_courant(journal):
    """
    Renvoie le dernier statut connu de chaque anomalie (id_piece + anomalie).

    Le journal etant un historique append-only, le statut courant est la
    decision la plus recente pour chaque couple (piece, anomalie).
    """
    if len(journal) == 0:
        return pd.DataFrame(columns=["id_piece", "anomalie", "statut", "horodatage", "utilisateur"])
    j = journal.sort_values("horodatage")
    dernier = j.groupby(["id_piece", "anomalie"]).tail(1)
    return dernier[["id_piece", "anomalie", "statut", "horodatage", "utilisateur"]]


def enrichir_avec_statut(detail, journal):
    """
    Ajoute au tableau d'anomalies le statut de traitement courant.
    Les anomalies jamais traitees sont 'À traiter' par defaut.
    """
    courant = statut_courant(journal)
    if len(courant) == 0:
        detail = detail.copy()
        detail["statut_traitement"] = "À traiter"
        return detail
    fusion = detail.merge(courant[["id_piece", "anomalie", "statut"]],
                          on=["id_piece", "anomalie"], how="left")
    fusion["statut_traitement"] = fusion["statut"].fillna("À traiter")
    return fusion.drop(columns=["statut"])


def synthese_traitement(detail_enrichi):
    """Indicateurs de suivi du traitement des anomalies."""
    total = len(detail_enrichi)
    if "statut_traitement" not in detail_enrichi.columns or total == 0:
        return {s: 0 for s in STATUTS} | {"total": total, "taux_traitement": 0}
    compte = detail_enrichi["statut_traitement"].value_counts().to_dict()
    traitees = total - compte.get("À traiter", 0)
    res = {s: int(compte.get(s, 0)) for s in STATUTS}
    res["total"] = total
    res["taux_traitement"] = round(traitees / total * 100, 1) if total else 0
    return res
