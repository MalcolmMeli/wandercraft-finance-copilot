# Wandercraft Finance Copilot

**Prototype d'automatisation du contrôle comptable — application Streamlit fonctionnelle.**

Application web à 8 modules qui exécute de vrais contrôles comptables sur 137 180 écritures synthétiques. L'outil détecte les anomalies, prépare les traitements et trace chaque décision.

> Principe : l'IA propose, l'humain valide — et sa décision est tracée.

## Les 8 modules (tous fonctionnels)
1. **Vue d'ensemble** — indicateurs, avancement du traitement
2. **Contrôle des factures** — 10 contrôles + prise en charge tracée (vrais filtres, vraies décisions)
3. **Rapprochement bancaire** — 78,6 % automatique + analyse des causes de non-match
4. **Préparation de clôture** — cut-off FNP / CCA / CAP (date paramétrable)
5. **Relances fournisseurs** — relances graduées + emails générés
6. **Assistant IA** — analyse en langage naturel via Gemini (répond vraiment)
7. **Journal & traçabilité** — audit trail horodaté
8. **Simulateur de gains** — estimation prudente interactive

## Lancer en local
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Assistant IA (optionnel)
Créez `.streamlit/secrets.toml` avec :
```
GEMINI_API_KEY = "votre_clé_gemini"
```
Clé gratuite sur aistudio.google.com. Sans clé, tous les autres modules fonctionnent.

## Déploiement sur Streamlit Community Cloud
1. Poussez ces fichiers sur GitHub
2. Sur share.streamlit.io, connectez le dépôt
3. Ajoutez la clé GEMINI_API_KEY dans les secrets de l'app
4. Obtenez votre lien public

## Architecture
Six couches séparées : données, règles métier, calculs déterministes, IA (rédactionnel), traçabilité (audit trail), exports. Les calculs ne dépendent jamais de l'IA.

## Données
Journal comptable (137 180 écritures sur 3 ans) + relevé bancaire (73 000 mouvements). Synthétiques, calibrés sur une ETI industrielle (~100 M€ charges/an).

---
*Prototype sur données synthétiques. Design premium, logique fonctionnelle.*
