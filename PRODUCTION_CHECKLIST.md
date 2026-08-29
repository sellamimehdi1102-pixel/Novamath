# PRODUCTION_CHECKLIST.md — Mise en production NovaMath (coût minimal)

Stratégie : Docker local (gratuit) → GitHub (gratuit) → Render Free/Starter
→ Resend (gratuit au départ) → un seul domaine (~10-20 €/an) → HTTPS
Render (gratuit, inclus). Stripe déjà en Live.

Convention : `[ ]` = à faire, action indiquée + où la faire + résultat
attendu + risque éventuel.

---

## PHASE 1 — Local

- [ ] **Action** : builder l'image Docker en local pour valider le pipeline.
  **Où** : `docker build -t novamath-production-test .` à la racine du
  dépôt. **Résultat attendu** : build réussi, image ~1 Go (déjà vérifié
  dans cette session — succès). **Risque** : aucun (opération locale,
  réversible).
- [ ] **Action** : vérifier `/api/health`, page d'accueil et assets
  statiques sur un conteneur de test local (`docker run -p 8001:8000 ...`).
  **Où** : local. **Résultat attendu** : `status: degraded` normal sans
  secrets configurés (Stripe/SMTP absents), `200` sur `/` et les assets.
  **Risque** : aucun.
- [ ] **Action** : lancer `pytest` (backend) et `vitest run` (frontend).
  **Où** : local (`cd webapp && python -m pytest tests/ -q` ;
  `npx vitest run` à la racine). **Résultat attendu** : mêmes 6-7 échecs
  préexistants déjà connus (non liés à la production), aucune nouvelle
  régression. **Risque** : aucun si aucun nouvel échec n'apparaît — sinon
  investiguer avant de continuer.

## PHASE 2 — GitHub

- [ ] **Action** : vérifier qu'aucun secret n'est suivi par Git avant de
  pousser (`git status`, `git diff`). **Où** : local. **Résultat attendu** :
  seul `Dockerfile`/`.dockerignore` (et les nouveaux fichiers de ce
  chantier) apparaissent modifiés — jamais `.env`. **Risque** : fuite de
  secret si un fichier suspect est commité par erreur — vérifier le
  contenu de chaque fichier avant `git add`.
- [ ] **Action** : committer et pousser sur la branche `main`. **Où**
  : local (`git add`, `git commit`, `git push`) — **à valider par vous**,
  cette session ne pousse jamais sans confirmation explicite. **Résultat
  attendu** : le dépôt GitHub reflète l'état corrigé (Dockerfile
  fonctionnel, `.dockerignore` sécurisé). **Risque** : aucun (`push` sur
  `main` reste une action visible/partagée — confirmation requise).
- [ ] **Action** (recommandée, hors périmètre de cette session — nécessite
  votre accord) : envisager de retirer `versions/*/data/novamath.db`
  (~180 Mo cumulés) et `graphify-out/graph.json` (78 Mo) du suivi Git pour
  garder des clones/déploiements rapides. **Où** : à discuter avec vous
  avant toute réécriture d'historique. **Risque** : réécriture d'historique
  Git — jamais fait automatiquement, voir règles de cette mission.

## PHASE 3 — Domaine

- [ ] **Action** : choisir et acheter UN domaine (~10-20 €/an, ex. `.fr`
  ou `.com` selon disponibilité réelle — à vérifier vous-même chez un
  registrar, aucune disponibilité n'est garantie ici). **Où** : registrar
  de votre choix (OVH, Gandi, Namecheap...). **Résultat attendu** :
  domaine actif, accès à la zone DNS. **Risque** : aucun côté dépôt — achat
  externe, à votre charge.
- [ ] **Action** : créer l'enregistrement DNS pointant vers Render (Render
  indique la valeur exacte après ajout du domaine custom, voir
  RENDER_SETUP.md étape 10). **Où** : zone DNS du registrar. **Résultat
  attendu** : propagation DNS effective (quelques minutes à quelques
  heures), domaine résolu vers Render. **Risque** : action DNS — à vous de
  la réaliser, cette session ne peut pas y accéder.

## PHASE 4 — Resend

- [ ] **Action** : ajouter votre domaine dans Resend (dashboard Resend >
  Domains). **Où** : dashboard Resend. **Résultat attendu** : Resend
  fournit les enregistrements DNS à créer (SPF, DKIM, éventuellement un
  enregistrement de retour DMARC recommandé). **Risque** : aucun.
- [ ] **Action** : créer ces enregistrements DNS (SPF `TXT`, DKIM
  généralement `CNAME` ou `TXT` selon Resend, DMARC `TXT` optionnel mais
  recommandé). **Où** : zone DNS du registrar (même domaine que Phase 3).
  **Résultat attendu** : domaine marqué "Verified" dans Resend. **Risque** :
  action DNS externe — à vous de la réaliser.
- [ ] **Action** : générer une clé API/SMTP Resend et renseigner
  `EMAIL_SMTP_*`/`EMAIL_FROM_ADDRESS` dans Render (jamais dans un fichier
  Git). **Où** : dashboard Resend puis Render > Environment. **Résultat
  attendu** : `check_smtp_configured` (page Santé admin) passe à `true`.
  **Risque** : aucun si la clé reste hors Git.

## PHASE 5 — Render

- [ ] **Action** : suivre intégralement `RENDER_SETUP.md` (créer le Web
  Service, choisir Docker, configurer port/variables/health check).
  **Où** : dashboard Render. **Résultat attendu** : service déployé,
  accessible via `https://xxxx.onrender.com`. **Risque** : aucun sur le
  plan Free ; **coût** si passage au plan Starter pour le disque
  persistant (voir Phase 5bis).
- [ ] **DÉCISION REQUISE — persistance SQLite** : sans disque persistant
  Render (fonctionnalité payante, absente du plan Free), `data/novamath.db`
  est réinitialisé à chaque redéploiement/réveil après veille. **Où** :
  Render > Disks (nécessite plan Starter, ~7 $/mois + ~0,25 $/Go/mois).
  **Résultat attendu** : disque monté sur `/app/data`,
  `BACKUP_DIRECTORY=/app/data/backups` positionnée (voir
  `.env.production.example`) — aucune modification de code nécessaire.
  **Risque** si non fait : perte de tous les comptes/statistiques à chaque
  redémarrage — acceptable UNIQUEMENT en test de marché sans compte réel.
- [ ] **Action** : connecter le domaine personnalisé (Phase 3) au service
  Render. **Où** : Render > Settings > Custom Domains. **Résultat
  attendu** : HTTPS actif automatiquement via Let's Encrypt (géré par
  Render, aucun achat séparé). **Risque** : aucun.

## PHASE 6 — Stripe

- [ ] **Action** : mettre à jour l'URL du endpoint webhook Stripe Live vers
  `https://votre-domaine.fr/api/checkout/webhook`. **Où** : Dashboard
  Stripe (mode Live) > Developers > Webhooks. **Résultat attendu** :
  Stripe signe et envoie les événements vers le bon domaine ;
  `STRIPE_WEBHOOK_SECRET` mis à jour dans Render avec le nouveau signing
  secret. **Risque** : **action sur un service externe en mode Live — à
  valider par vous**, cette session ne modifie jamais Stripe.
- [ ] **Action** : vérifier `STRIPE_SECRET_KEY`/`STRIPE_PUBLIC_KEY`/
  `STRIPE_PRICE_PREMIUM`/`STRIPE_PRICE_ULTRA` en Render correspondent bien
  aux vraies valeurs Live (jamais les valeurs Test Mode du `.env` local).
  **Où** : Render > Environment. **Résultat attendu** :
  `check_stripe_configured` passe à `true` dans `/api/health`. **Risque** :
  un paiement réel serait déclenché si un test est fait avec de vraies
  cartes — à ne faire qu'avec votre accord explicite.
- [ ] **Action** (votre initiative, non automatisée) : effectuer un
  paiement Live réel à faible montant pour valider le flux
  checkout → webhook → activation du plan. **Où** : votre site en
  production. **Risque** : paiement réel — à vous de décider du montant/du
  moment.

## PHASE 7 — Tests production

- [ ] **Action** : `curl -I https://votre-domaine.fr/api/health` depuis
  votre poste. **Où** : local, contre le domaine réel. **Résultat
  attendu** : réponse HTTPS valide (pas d'erreur de certificat), `"status":
  "ok"` une fois Stripe/SMTP configurés. **Risque** : aucun.
- [ ] **Action** : parcours utilisateur complet (inscription, connexion,
  navigation cours/exercices, page abonnement) sur le domaine réel. **Où** :
  navigateur, domaine réel. **Résultat attendu** : aucune erreur, aucune
  référence à `localhost` visible. **Risque** : aucun.
- [ ] **Action** : vérifier les en-têtes de sécurité en production
  (`curl -I` ou l'onglet Réseau du navigateur) : `Strict-Transport-Security`
  présent, `Content-Security-Policy` présent, cookies marqués `Secure`.
  **Où** : navigateur/`curl` contre le domaine réel. **Résultat attendu** :
  tous les en-têtes attendus présents (déjà implémentés dans le code, à
  confirmer une fois HTTPS actif). **Risque** : aucun.

## PHASE 8 — Ouverture publique

- [ ] **Action** : lever toute restriction d'accès temporaire éventuelle
  (aucune trouvée dans le code actuel — l'application est déjà servie
  publiquement dès le déploiement Render). **Où** : n/a. **Résultat
  attendu** : site accessible publiquement sur le domaine final. **Risque** :
  aucun.
- [ ] **Action** : surveiller les premiers jours via les logs Render
  (`Logs` du service) et `/api/health`. **Où** : dashboard Render.
  **Résultat attendu** : pas d'erreur 5xx inattendue, sauvegardes
  automatiques quotidiennes visibles dans les logs
  (`backup_scheduler`/`backup_service`). **Risque** : aucun, surveillance
  passive.
- [ ] **Action** (votre décision) : communiquer publiquement l'URL/domaine
  pour commencer le test de marché. **Où** : vos canaux de communication.
  **Risque** : aucun côté technique.
