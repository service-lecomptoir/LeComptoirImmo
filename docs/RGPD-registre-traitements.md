# Registre des activités de traitement (RGPD)

Document interne (art. 30 RGPD). À tenir à jour. `[À COMPLÉTER]` = information à renseigner.

## Responsable du traitement
- **Le Comptoir** (entreprise individuelle / auto-entrepreneur), Aronson ALPHANORD
- SIREN : 823 382 213 — TVA non applicable (art. 293 B CGI)
- Siège : **7 rue d'Alembert, 92600 Asnières-sur-Seine**
- Contact / référent données : Aronson ALPHANORD — service.lecomptoir@outlook.com

## Sous-traitants
| Sous-traitant | Rôle | Localisation |
|---|---|---|
| OVH SAS | Hébergement (serveurs, base de données) | France |
| Stripe | Paiements en ligne | UE / USA (clauses contractuelles types) |
| Brevo (Sendinblue) | Envoi d'e-mails transactionnels | UE |

## Traitements

### 1. Gestion locative
- **Finalité** : gérer les baux, loyers, quittances, avis d'échéance.
- **Base légale** : exécution du contrat ; obligation légale (comptabilité).
- **Personnes** : locataires, propriétaires.
- **Données** : identité, coordonnées, date/lieu de naissance, RIB, montants, paiements.
- **Conservation** : 3 ans après la fin du bail (puis anonymisation) ; pièces comptables jusqu'à 10 ans.
- **Destinataires** : gestionnaire, propriétaire concerné, sous-traitants ci-dessus.

### 2. Candidatures de location
- **Finalité** : étudier les dossiers de candidature à un logement.
- **Base légale** : mesures précontractuelles.
- **Personnes** : candidats locataires.
- **Données** : identité, coordonnées, situation professionnelle, revenus, pièces justificatives.
- **Conservation** : 12 mois après refus (puis anonymisation) ; dossier retenu → bascule en gestion locative.
- **Destinataires** : gestionnaire.

### 3. Comptes utilisateurs & sécurité
- **Finalité** : authentification, gestion des accès, journal d'audit.
- **Base légale** : intérêt légitime (sécurité) ; exécution du contrat.
- **Données** : e-mail, mot de passe (haché), rôle, journaux d'accès (IP, action, horodatage).
- **Conservation** : durée du compte ; journaux d'audit **[durée à définir, ex. 12 mois]**.

### 4. Communications
- **Finalité** : envoi des avis, quittances, relances (e-mail/SMS).
- **Base légale** : exécution du contrat ; obligation légale.
- **Conservation** : journal des envois lié à la période concernée.

## Droits des personnes
- Accès, rectification, effacement, portabilité, limitation, opposition.
- **Mise en œuvre dans l'application** : export et anonymisation d'un locataire (menu RGPD / API `/rgpd`), tracés au journal d'audit.
- Réclamation : CNIL (cnil.fr).

## Mesures de sécurité
- Chiffrement des secrets (clés de paiement), HTTPS, accès restreints par rôle.
- Sauvegardes quotidiennes des bases + test de restauration hebdomadaire.
- Anonymisation automatique des données expirées (batch mensuel).
