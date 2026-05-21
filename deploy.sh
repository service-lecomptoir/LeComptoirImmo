#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# deploy.sh — Script de déploiement Locataire Cloud sur VPS
#
# Usage (sur le VPS) :
#   chmod +x deploy.sh
#   ./deploy.sh              # Premier déploiement
#   ./deploy.sh --update     # Mise à jour (pull + rebuild + restart)
#   ./deploy.sh --ssl        # Obtenir/renouveler le certificat SSL
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="docker compose -f ${APP_DIR}/docker/docker-compose.prod.yml"
DOMAIN="${DOMAIN:-votre-domaine.fr}"
EMAIL="${EMAIL:-admin@votre-domaine.fr}"

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Vérifications préalables ──────────────────────────────────────────────────
check_requirements() {
    command -v docker >/dev/null 2>&1 || error "Docker non installé. Voir https://docs.docker.com/engine/install/"
    docker compose version >/dev/null 2>&1 || error "Docker Compose v2 requis."
    [[ -f "${APP_DIR}/backend/.env" ]] || error "Fichier backend/.env manquant. Copier .env.example et compléter les valeurs."
}

# ── SSL : obtenir le certificat Let's Encrypt ─────────────────────────────────
setup_ssl() {
    info "Obtention du certificat SSL pour ${DOMAIN}..."

    # Démarrer uniquement nginx pour le challenge ACME
    ${COMPOSE} up -d nginx

    sleep 3

    docker compose -f "${APP_DIR}/docker/docker-compose.prod.yml" run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        -d "${DOMAIN}" \
        -d "www.${DOMAIN}"

    success "Certificat SSL obtenu pour ${DOMAIN}"
    info "Redémarrage de nginx avec SSL..."
    ${COMPOSE} restart nginx
}

# ── Premier déploiement ───────────────────────────────────────────────────────
first_deploy() {
    info "=== Premier déploiement Locataire Cloud ==="

    check_requirements

    # Vérifier que le domaine est configuré dans nginx-site.conf
    if grep -q "votre-domaine.fr" "${APP_DIR}/docker/nginx-site.conf"; then
        warn "Le domaine n'a pas été configuré dans docker/nginx-site.conf"
        warn "Remplacez 'votre-domaine.fr' par votre vrai domaine avant de continuer."
        read -rp "Continuer quand même ? [y/N] " confirm
        [[ "${confirm:-N}" =~ ^[Yy]$ ]] || exit 1
    fi

    info "Construction et démarrage des conteneurs..."
    ${COMPOSE} up -d --build

    info "En attente de la base de données..."
    sleep 10

    info "Vérification de l'état des services..."
    ${COMPOSE} ps

    success "=== Déploiement terminé ==="
    info "Backend  : http://localhost:8000/health"
    info "Logs     : docker compose -f docker/docker-compose.prod.yml logs -f"
}

# ── Mise à jour ───────────────────────────────────────────────────────────────
update_deploy() {
    info "=== Mise à jour Locataire Cloud ==="

    check_requirements

    info "Pull des dernières modifications Git..."
    git -C "${APP_DIR}" pull origin main

    info "Rebuild et redémarrage des conteneurs modifiés..."
    ${COMPOSE} up -d --build --remove-orphans

    info "Nettoyage des images obsolètes..."
    docker image prune -f

    info "État des services :"
    ${COMPOSE} ps

    success "=== Mise à jour terminée ==="
}

# ── Statut ────────────────────────────────────────────────────────────────────
show_status() {
    info "=== Statut Locataire Cloud ==="
    ${COMPOSE} ps
    echo ""
    info "Health check backend :"
    curl -sf http://localhost:8000/health 2>/dev/null && echo "" || warn "Backend non accessible"
}

# ── Renouvellement SSL (à mettre dans cron) ───────────────────────────────────
renew_ssl() {
    info "Renouvellement du certificat SSL..."
    ${COMPOSE} run --rm certbot renew --quiet
    ${COMPOSE} restart nginx
    success "Certificat renouvelé"
}

# ── Point d'entrée ────────────────────────────────────────────────────────────
case "${1:-}" in
    --update)   update_deploy ;;
    --ssl)      setup_ssl ;;
    --renew-ssl) renew_ssl ;;
    --status)   show_status ;;
    "")         first_deploy ;;
    *)
        echo "Usage: $0 [--update | --ssl | --renew-ssl | --status]"
        exit 1
        ;;
esac
