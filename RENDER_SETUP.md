# RENDER_SETUP.md — Déploiement Mathadap sur Render

Instructions pour VOUS (aucune action ici n'est automatisable depuis le
dépôt : compte Render, GitHub, domaine et secrets vous appartiennent).
Aucun secret n'est écrit dans ce fichier.

Prérequis avant de commencer : le dépôt doit être poussé sur GitHub (voir
PRODUCTION_CHECKLIST.md, Phase 2).

---

## 1. Créer le Web Service

1. https://dashboard.render.com > **New** > **Web Service**.
2. **Build and deploy from a Git repository** > connecter votre compte
   GitHub si ce n'est pas déjà fait > sélectionner le dépôt `novamath`
   (ou le nom réel de votre dépôt).

## 2. Connecter GitHub

Déjà fait à l'étape 1 si vous avez autorisé l'accès au dépôt. Render
détecte automatiquement les nouveaux commits sur la branche choisie
(`main`) et propose un redéploiement automatique (activable/désactivable
dans **Settings > Auto-Deploy**).

## 3. Choisir Docker comme environnement

Dans **Language/Runtime**, sélectionner **Docker**. Render détecte
automatiquement le `Dockerfile` à la racine du dépôt — aucune commande
`docker build` manuelle à fournir.

- **Dockerfile Path** : `./Dockerfile` (déjà le défaut).
- **Docker Build Context Directory** : `.` (racine du dépôt).

## 4. Configurer le port

Rien à faire manuellement : `gunicorn.conf.py` lit automatiquement la
variable `PORT` injectée par Render (`bind = 0.0.0.0:$PORT`). Ne définissez
JAMAIS `PORT` vous-même dans les variables d'environnement Render.

## 5. Configurer les variables d'environnement

Dans **Environment** > **Environment Variables**, ajouter une par une les
variables listées dans `.env.production.example` (à la racine du dépôt) —
copier le NOM, jamais un placeholder tel quel. Au minimum pour un
démarrage fonctionnel :

- `FLASK_ENV=production`
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLIC_KEY`, `STRIPE_PRICE_PREMIUM`,
  `STRIPE_PRICE_ULTRA`, `STRIPE_WEBHOOK_SECRET` (valeurs **Live**)
- `APP_BASE_URL=https://votre-domaine.fr`
- `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USERNAME`,
  `EMAIL_SMTP_PASSWORD`, `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` (Resend)
- `BACKUP_DIRECTORY=/app/data/backups` (voir étape 6 — nécessite le disque
  persistant monté sur `/app/data`)

Ne PAS définir `DATABASE_URL` (SQLite reste le mode par défaut, voir
PRODUCTION_CHECKLIST.md Phase 5 pour la justification).

## 6. Configurer le disque persistant — DÉCISION REQUISE

**Important, à trancher avant de continuer** : le plan **Render Free ne
propose pas de disque persistant** (fonctionnalité réservée aux instances
payantes, "Starter" ~7 $/mois minimum + coût du disque, ~0,25 $/Go/mois).
Sans disque persistant, `data/novamath.db` (comptes, abonnements liés à
Stripe, statistiques) est réinitialisé à **chaque redéploiement et à
chaque réveil après mise en veille** (le plan Free met le service en
veille après ~15 min d'inactivité).

Deux options :

- **Option A (recommandée dès qu'il y a de vrais comptes/paiements)** :
  passer l'instance en plan **Starter**, puis dans **Disks** > **Add Disk**
  > **Mount Path** = `/app/data`, taille 1 Go suffit pour démarrer
  (extensible plus tard sans perte de données). Avec `BACKUP_DIRECTORY=
  /app/data/backups` (étape 5), les sauvegardes vivent aussi sur ce même
  disque — aucune modification de code nécessaire.
- **Option B (test de marché pur, sans compte réel)** : rester sur Free
  sans disque, en acceptant que toute donnée soit éphémère. À réserver à
  une phase où aucun vrai utilisateur ne crée de compte/paie réellement.

## 7. Configurer le health check

Dans **Settings** > **Health Check Path**, renseigner :

```
/api/health
```

Render considère l'instance "up" sur toute réponse HTTP (y compris 503),
sauf configuration plus stricte — le `HEALTHCHECK` du Dockerfile est
distinct et sert uniquement au diagnostic `docker inspect` local, il n'est
pas utilisé par Render. Vérifiez après déploiement (étape 12) que
`/api/health` renvoie `"status": "ok"` une fois Stripe/SMTP configurés
(un `"degraded"` avec `stripe_configured: false` avant configuration des
clés Live est normal, voir étape 5).

## 8. Déployer

**Create Web Service** (bas de page). Render lance automatiquement le
build Docker (`builder` → `frontend-builder` → `final`, voir Dockerfile)
puis démarre le conteneur avec `gunicorn -c gunicorn.conf.py
webapp.server:app`. Suivre les logs de build en direct dans l'onglet
**Logs**.

## 9. Récupérer l'URL

Une fois déployé, Render fournit une URL du type
`https://novamath-xxxx.onrender.com` (visible en haut de la page du
service). HTTPS déjà actif automatiquement sur cette URL (certificat
Render).

## 10. Connecter le domaine personnalisé

Dans **Settings** > **Custom Domains** > **Add Custom Domain**, saisir
votre domaine (ex. `votre-domaine.fr` et/ou `www.votre-domaine.fr`).
Render indique alors l'enregistrement DNS exact à créer chez votre
registrar (généralement un `CNAME` vers `<service>.onrender.com` pour un
sous-domaine, ou un enregistrement `ALIAS`/`ANAME` pour l'apex — Render
affiche la valeur précise pour votre cas). Voir PRODUCTION_CHECKLIST.md
Phase 3 pour le détail. **Action DNS : à vous de la réaliser chez votre
registrar**, ce dépôt ne peut pas le faire.

## 11. Configurer HTTPS

Automatique : dès que le DNS pointe correctement vers Render (propagation
pouvant prendre de quelques minutes à quelques heures), Render provisionne
et renouvelle seul un certificat Let's Encrypt pour votre domaine — aucun
achat de certificat séparé, rien à faire de plus ici.

## 12. Tester

Une fois le domaine actif en HTTPS :

1. `curl -I https://votre-domaine.fr/api/health` — doit répondre (200 ou
   503 selon config Stripe/SMTP, jamais une erreur de connexion/certificat).
2. Vérifier dans le navigateur : page d'accueil, création de compte,
   connexion.
3. **Stripe** : mettre à jour dans le Dashboard Stripe (mode **Live**)
   l'URL du endpoint webhook vers
   `https://votre-domaine.fr/api/checkout/webhook`, puis déclencher un
   paiement de test réel à faible montant si vous souhaitez valider le
   flux de bout en bout (voir PRODUCTION_CHECKLIST.md Phase 6 — action
   sur un service externe, à votre initiative).
4. **Resend** : vérifier qu'un email transactionnel réel (ex. lien de
   consentement parental) part bien et n'atterrit pas en spam.
5. Revérifier `/api/health` : tous les checks doivent passer à `true` une
   fois Stripe/SMTP correctement configurés en production.

---

**Comportement après redémarrage/redéploiement** : sans disque persistant
(étape 6, option B), les données sont perdues à chaque redémarrage —
attendu et documenté, pas un bug. Avec disque persistant (option A),
`data/` (et donc `backups/` via `BACKUP_DIRECTORY`) survit à tous les
redéploiements et redémarrages, y compris un changement d'image Docker.
