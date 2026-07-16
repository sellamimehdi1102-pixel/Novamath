# Changelog — NovaMath v1.00

**Date** : 2026-07-11

## Contexte
Renommage complet de l'identité du projet : **Lumis → NovaMath**. Aucune fonctionnalité existante n'est
modifiée, ce changement ne concerne que l'identité visible (nom, titres, métadonnées, README) et le
versionnement (repart à v1.00 sous le nouveau préfixe). Les archives `versions/Lumis_V1` à `Lumis_V6`
restent intactes et documentent l'historique sous l'ancien nom.

## Fonctionnalités ajoutées
- Aucune.

## Fonctionnalités supprimées
- Aucune.

## Corrections de bugs
- Aucune (hors travail d'identité ci-dessous).

## Renommage d'identité
- Toutes les pages (`index.html`, `dashboard.html`, `chapitres.html`, `evaluation.html`,
  `exercice.html`, `profil.html`) : titres `<title>`, texte de marque dans le header, footer, FAQ et
  paragraphes marketing de la landing page passent de "Lumis" à "NovaMath".
- `assets/logo.svg` : `aria-label` mis à jour ("NovaMath"). Le tracé du logo (dégradé indigo/violet
  abstrait, sans texte intégré) est conservé tel quel — déjà cohérent avec la nouvelle identité et
  utilisé comme favicon.
- `css/tokens.css` : commentaire d'en-tête mis à jour.
- `webapp/server.py` : docstring d'en-tête mis à jour ("AdaptiveMath" → "NovaMath" — trace interne
  historique invisible côté utilisateur).
- `06_quiz_app.py` (script Gradio legacy, remplacé par ce backend Flask mais conservé) : titre affiché
  "AdaptiveMath — Seconde" → "NovaMath — Seconde".
- `create_version_snapshot.py` : `PRODUCT_NAME` passe à "NovaMath" ; le compteur de version repart à
  v1.00 sous ce nouveau préfixe.
- Nouveau `README.md` à la racine du projet (aucun README n'existait auparavant).
- Identifiants techniques **volontairement non renommés** (risque de casse / perte de données locales
  sans bénéfice visible) : préfixe `lumis:` des clés `localStorage` (`lumis:stats`, `lumis:profile`,
  `lumis:theme`, `lumis:practice_choices`, `lumis:last_level`, `lumis:pending_series`,
  `lumis:selected_chapters`, `lumis:open_chapter`, `lumis:series_in_progress`), noms d'animations CSS
  (`lumis-modal-fade`, `lumis-modal-pop`, `lumis-confetti-fall`, `lumis-shake`, `lumis-fade-in`),
  id SVG `lumis-grad`. Renommer ces clés ferait perdre le thème, les stats en cache et toute série en
  cours déjà sauvegardée dans le navigateur des utilisateurs existants, sans aucun impact visible côté
  utilisateur.

## Améliorations UI
- Aucune.

## Améliorations UX
- Aucune.

## Optimisations
- Aucune.

## Bugs connus
- Aucun lié à ce changement.
