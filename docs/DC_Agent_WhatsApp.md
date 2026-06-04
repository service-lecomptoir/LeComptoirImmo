# DC — Dossier de Conception · Agent IA WhatsApp pour gestionnaires

> Objet : un **agent conversationnel** qui contacte les gestionnaires sur **WhatsApp**
> pour (1) leur envoyer des **rappels** proactifs, (2) répondre à leurs **questions**,
> (3) **prendre des instructions** et les exécuter via l'API Le Comptoir Immo.
> Public : décision produit + équipe technique. Statut : conception (v1).
>
> ⚠️ Aucun secret dans ce document. Les jetons/identifiants vivront dans `.env.prod`.

---

## 1. Objectifs

- **Gagner du temps** au gestionnaire : être notifié et agir sans ouvrir l'app.
- **Proactivité** : rappels d'échéances, impayés, maintenances dues, démarches en attente, baux à renouveler.
- **Conversation naturelle** : poser une question (« quels loyers manquent ce mois ? ») ou donner une instruction (« envoie la quittance de M. X »).
- **Réutiliser l'existant** : l'application porte déjà tout le métier (paiements, quittances, démarches, entretiens/autoplan, scoring, baux). L'agent ne fait qu'**orchestrer** ces fonctions.

### Hors périmètre v1
- Pas de communication WhatsApp avec les **locataires/propriétaires** (gestionnaires seulement).
- Pas de pièces jointes sensibles sur WhatsApp (cf. §7 RGPD) — on envoie un lien vers l'app pour le détail.

---

## 2. Le canal WhatsApp (contraintes structurantes)

WhatsApp impose l'**API officielle WhatsApp Business** (Meta **Cloud API**, ou via un fournisseur : Twilio, 360dialog, MessageBird). Points clés :

| Contrainte | Conséquence de conception |
|---|---|
| **Numéro WhatsApp Business** dédié + vérification entreprise Meta | À provisionner avant tout développement |
| **Templates pré-approuvés (HSM)** obligatoires pour les messages **sortants proactifs** | Les rappels passent par un **catalogue de templates** validés par Meta (cf. §6) |
| **Fenêtre de service 24 h** : réponse libre seulement dans les 24 h après un message du gestionnaire | Hors fenêtre → on doit relancer via un template |
| **Opt-in explicite** requis | Étape d'activation + consentement enregistré (cf. §4) |
| **Facturation par conversation** (≈ centimes, variable pays/catégorie) | Budgéter ; limiter les rappels au pertinent |

> **Alternative / démarrage rapide** : le **même agent** peut fonctionner d'abord par **e-mail** ou via un **chat intégré à l'app** (pas de dépendance Meta, pas de templates), puis WhatsApp en surcouche.

---

## 3. Architecture cible

```
                 ┌──────────────────────────────────────────────┐
   WhatsApp      │            Le Comptoir Immo (backend)         │
  (gestionnaire) │                                              │
       │  msg →   │  /webhooks/whatsapp  ──►  Service Agent IA   │
       │◄─ rép.   │        (entrant)            (Claude + outils) │
       │          │                                  │           │
       │          │                                  ▼           │
       │          │     Outils = endpoints métier existants :    │
       │          │   paiements · quittances · démarches ·       │
       │          │   entretiens/autoplan · scoring · baux       │
       │          │                                              │
       │◄─ rappel │   Scheduler ──► Générateur de rappels ──►    │
       │ (template)│   Service d'envoi WhatsApp (sortant)         │
       └──────────┤                                              │
                  │   Table de liaison : gestionnaire ↔ numéro   │
                  │   (opt-in, jeton, préférences, journal)      │
                  └──────────────────────────────────────────────┘
                        Fournisseur WhatsApp (Meta Cloud API)
```

- **Entrant** : un webhook FastAPI reçoit les messages → vérifie la signature → identifie le gestionnaire (via le numéro) → transmet à l'agent.
- **Agent IA** : interprète, appelle les outils (endpoints), formule une réponse, **demande confirmation** pour les actions sensibles.
- **Sortant proactif** : le scheduler (déjà présent pour les avis) déclenche le **générateur de rappels** qui envoie des templates.
- **Hébergement possible** : nouveau module backend, ou porté par le compagnon **Alice** (déjà branché à la même base et au réseau interne).

---

## 4. Modèle de données (nouveau)

Table `manager_whatsapp_link` (1 par gestionnaire qui active le canal) :

| Champ | Type | Rôle |
|---|---|---|
| `user_id` | FK users | Le gestionnaire |
| `phone_e164` | str | Numéro au format international (ex. +5949…) |
| `opt_in_at` | datetime | Date de consentement (RGPD) |
| `opt_out_at` | datetime? | Désinscription |
| `verify_code` / `verified_at` | str / datetime | Vérification du numéro (code envoyé une fois) |
| `prefs` | JSONB | Quels rappels, horaires, fréquence |
| `last_inbound_at` | datetime | Pour gérer la fenêtre 24 h |

Table `whatsapp_message_log` (audit + idempotence) :
`id, user_id, direction (in/out), template_name?, body_excerpt, status, provider_id, created_at`.

> Principe : on **stocke des extraits non sensibles** et des identifiants techniques, pas de PII détaillée.

---

## 5. L'agent IA (orchestration)

- **Modèle** : Claude, avec un **jeu d'outils** = sous-ensemble contrôlé des endpoints (lecture + actions autorisées).
- **Contexte** : l'agent reçoit l'identité du gestionnaire (rôle, périmètre) → **isolation respectée** (un gestionnaire ne voit/agit que sur son périmètre, comme dans l'app).
- **Boucle** : message → intention → (consultation OU action) → réponse.
- **Garde-fous** :
  - actions **modifiantes** (marquer payé, envoyer quittance, planifier entretien) → **récapitulatif + confirmation** (« Réponds OUI pour valider ») ;
  - **journalisation** de chaque action (qui, quoi, quand) ;
  - refus poli hors périmètre / hors droits.

### Exemples d'outils exposés
| Intention | Outil (endpoint) |
|---|---|
| « quels loyers manquent ce mois ? » | liste paiements en retard (lecture) |
| « score de M. X ? » | `/scoring/{tenant}` (lecture) |
| « envoie la quittance de mai à M. X » | `/payments/{id}/quittance/send` (action + confirmation) |
| « marque le loyer d'avril payé » | `/payments/{id}/record` (action + confirmation) |
| « planifie une révision chaudière chez Y » | création d'entretien (action + confirmation) |

---

## 6. Catalogue de rappels proactifs (templates Meta)

Réutilise les signaux déjà calculés par l'app :

| Rappel | Source existante | Fréquence suggérée |
|---|---|---|
| Loyers en retard | paiements en retard | quotidien (matin) |
| Échéances à venir | avis d'échéance | hebdomadaire |
| Mauvais payeurs / risque | **scoring** (note D/E) | hebdomadaire |
| Maintenances dues | **entretiens / autoplan** | hebdomadaire |
| Démarches en attente | **module Démarche** | quotidien si en retard |
| Baux à renouveler | dates de fin de bail | mensuel |

Chaque rappel = un **template approuvé** (texte sobre + variables) renvoyant vers l'app pour le détail. Préférences par gestionnaire (`prefs`) : choisir les rappels et l'horaire.

---

## 7. Sécurité, RGPD & gouvernance

- **Consentement** : opt-in explicite, opt-out à tout moment (« STOP »).
- **Minimisation des données** : pas de RIB, n° de sécurité sociale ni détail financier complet sur WhatsApp ; messages sobres + lien sécurisé vers l'app.
- **Authentification** : numéro rattaché à un compte vérifié (code unique) ; jeton de liaison ; expiration de session.
- **Confirmation** des actions modifiantes ; **journal d'audit** complet.
- **Sécurité technique** : vérification de la **signature du webhook**, secrets en `.env.prod` (hors Git), rate-limiting.
- **Isolation rôle** : l'agent applique le même périmètre que l'app (mandataire hors GP, GP = son périmètre).

---

## 8. Configuration (clés `.env.prod` à ajouter)

```
WHATSAPP_PROVIDER=meta            # meta | twilio | 360dialog
WHATSAPP_PHONE_NUMBER_ID=<À_RENSEIGNER>
WHATSAPP_BUSINESS_ACCOUNT_ID=<À_RENSEIGNER>
WHATSAPP_TOKEN=<À_RENSEIGNER>     # jeton d'accès (long-lived)
WHATSAPP_VERIFY_TOKEN=<À_RENSEIGNER>   # vérification du webhook
WHATSAPP_APP_SECRET=<À_RENSEIGNER>     # signature des requêtes entrantes
AGENT_LLM_API_KEY=<À_RENSEIGNER>       # clé du modèle IA
```

---

## 9. Plan de livraison par phases

### Phase 1 — Rappels sortants (faible risque, valeur immédiate)
- Provisionner numéro + compte Meta ; faire approuver 3-4 templates.
- Table de liaison + opt-in (écran « Mes informations »).
- Brancher le scheduler → 2-3 rappels (loyers en retard, maintenances dues, démarches en attente).
- **Recette** : un gestionnaire opt-in reçoit le bon rappel, opt-out fonctionne.

### Phase 2 — Agent en lecture (consultations)
- Webhook entrant + identification + agent **lecture seule** (paiements, scoring, démarches).
- **Recette** : questions répondues correctement, périmètre respecté, hors-droits refusé.

### Phase 3 — Prise d'instructions (actions)
- Outils modifiants avec **confirmation** + journalisation.
- **Recette** : action exécutée seulement après confirmation, trace d'audit présente, isolation rôle vérifiée.

---

## 10. Estimation & risques

- **Effort** : Phase 1 modérée ; Phases 2-3 plus lourdes (agent + sécurité).
- **Dépendances externes** : validation Meta (numéro, templates) = délai non maîtrisé en interne.
- **Coût récurrent** : facturation Meta par conversation + coût du modèle IA.
- **Risque principal** : fuite de données sensibles via un canal grand public → mitigé par la minimisation (§7).
- **Alternative de démarrage** : agent **e-mail / chat in-app** (sans dépendance Meta) pour valider l'usage avant WhatsApp.

---

## 11. Décisions à prendre (avant développement)

1. **Fournisseur** : Meta Cloud API en direct, ou via Twilio/360dialog (plus simple, surcoût) ?
2. **Canal de démarrage** : WhatsApp directement, ou e-mail/in-app d'abord ?
3. **Périmètre Phase 1** : quels 3 rappels prioritaires ?
4. **Modèle IA** : quel fournisseur / budget pour l'agent ?
5. **Politique d'actions** : jusqu'où autoriser les actions modifiantes par message ?
