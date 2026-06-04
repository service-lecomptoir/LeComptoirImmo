# -*- coding: utf-8 -*-
"""Génère des PDF soignés (DE + DI) pour Le Comptoir Immo via xhtml2pdf (pisa).
Usage : python docs/_gen_docs_pdf.py
Sortie : docs/DI_Dossier_Installation.pdf , docs/DE_Dossier_Exploitation.pdf
"""
import os
from html import escape
from xhtml2pdf import pisa

HERE = os.path.dirname(__file__)
DATE = "3 juin 2026"

NAVY = "#0D2F5C"; BLUE = "#2563EB"; ORANGE = "#EB690B"; TEAL = "#0E9F8E"
INK = "#1f2937"; GRAY = "#6b7280"

CSS = f"""
@page {{
  size: a4 portrait;
  margin: 1.7cm 1.5cm 1.6cm 1.5cm;
  @frame footer_frame {{ -pdf-frame-content: footerContent;
    bottom: 0.9cm; margin-left: 1.5cm; margin-right: 1.5cm; height: 0.8cm; }}
}}
body {{ font-family: Helvetica, Arial, sans-serif; color: {INK}; font-size: 10pt; line-height: 1.45; }}
h2 {{ color: {NAVY}; font-size: 15pt; margin: 14px 0 6px 0; border-bottom: 2.5px solid {ORANGE};
  padding-bottom: 3px; -pdf-keep-with-next: true; }}
h3 {{ color: {BLUE}; font-size: 11.5pt; margin: 10px 0 3px 0; -pdf-keep-with-next: true; }}
p {{ margin: 4px 0; }}
ul, ol {{ margin: 4px 0 7px 0; }}
li {{ margin: 1px 0; }}
b, strong {{ color: {NAVY}; }}
.lead {{ color: {GRAY}; font-size: 10.5pt; }}
.small {{ font-size: 8.2pt; color: {GRAY}; }}
.num {{ background: {NAVY}; color: #fff; font-size: 10pt; padding: 1px 7px; border-radius: 9px; margin-right: 6px; }}
.code {{ background: {NAVY}; color: #eaf0f7; font-family: "Courier New", monospace; font-size: 7.7pt;
  padding: 8px 10px; border-radius: 6px; border-left: 4px solid {TEAL}; -pdf-keep-in-frame-mode: shrink; }}
code {{ font-family: "Courier New", monospace; background: #eef2f7; color: #b8350b; font-size: 8.6pt; padding: 0 3px; }}
table.data {{ -fs-table-paginate: paginate; width: 100%; border-collapse: collapse; margin: 7px 0; font-size: 8.8pt; }}
table.data th {{ background: {NAVY}; color: #fff; text-align: left; padding: 6px 8px; }}
table.data td {{ padding: 5px 8px; border-bottom: 1px solid #e5e7eb; }}
.callout {{ border-left: 5px solid {GRAY}; padding: 8px 12px; margin: 9px 0; }}
.callout .t {{ font-weight: bold; margin-bottom: 2px; }}
.info {{ background: #eff6ff; border-color: {BLUE}; }}
.warn {{ background: #fffbeb; border-color: #d97706; }}
.danger {{ background: #fef2f2; border-color: #dc2626; }}
.tip {{ background: #ecfdf5; border-color: {TEAL}; }}
.badge {{ background: {GRAY}; color: #fff; font-size: 7.6pt; padding: 1px 7px; border-radius: 8px; }}
.b-navy {{ background: {NAVY}; }} .b-blue {{ background: {BLUE}; }} .b-orange {{ background: {ORANGE}; }}
.b-teal {{ background: {TEAL}; }} .b-gray {{ background: {GRAY}; }}
.footer {{ font-size: 7.5pt; color: #9aa1ab; text-align: right; }}
"""


def footer():
    return ('<div id="footerContent" class="footer">Le Comptoir Immo · Support / Exploitation '
            '&nbsp;—&nbsp; Page <pdf:pagenumber> / <pdf:pagecount></div>')


def cover(title, subtitle, role):
    return f"""
    <table width="100%" style="height: 25.2cm;" cellpadding="0" cellspacing="0">
      <tr><td valign="middle" align="center" bgcolor="{NAVY}" style="color:#ffffff;">
        <table width="78%" cellpadding="0" cellspacing="0"><tr><td style="color:#ffffff;">
          <div style="font-size:15pt; font-weight:bold; color:#ffffff;">LCI · Le Comptoir Immo</div>
          <div style="font-size:10pt; color:#9fc0e8; letter-spacing:2px; margin-top:34px;">{escape(role.upper())}</div>
          <div style="font-size:34pt; font-weight:bold; color:#ffffff; margin-top:4px;">{escape(title)}</div>
          <div style="font-size:13pt; color:#cfe0f3; margin-top:6px;">{escape(subtitle)}</div>
          <div style="margin-top:26px; font-size:9.5pt; color:#bcd2ec;">
            FastAPI · React/Vite &nbsp;|&nbsp; Docker Compose &nbsp;|&nbsp; PostgreSQL · Nginx · Let's Encrypt
          </div>
          <div style="margin-top:42px; border-top:1px solid #3a5d8f; padding-top:12px; font-size:9.5pt; color:#cfe0f3;">
            <b style="color:#ffffff;">Projet :</b> Le Comptoir Immo &amp; Alice &nbsp;·&nbsp;
            <b style="color:#ffffff;">Version :</b> 1.0 &nbsp;·&nbsp;
            <b style="color:#ffffff;">Date :</b> {DATE}<br/>
            <b style="color:#ffffff;">Domaines :</b> immo.lecomptoir.services · alice.lecomptoir.services<br/>
            <span style="color:#9fc0e8;">Document confidentiel. Aucun secret inclus — les valeurs sensibles
            vivent dans les .env.prod (hors Git).</span>
          </div>
        </td></tr></table>
      </td></tr>
    </table>
    <div style="page-break-after: always;"></div>
    """


def co(kind, title, body_html):
    return f'<div class="callout {kind}"><div class="t">{title}</div>{body_html}</div>'


def table(headers, rows):
    h = "".join(f"<th>{c}</th>" for c in headers)
    body = ""
    for i, r in enumerate(rows):
        bg = ' bgcolor="#f6f8fb"' if i % 2 else ""
        body += "<tr>" + "".join(f"<td{bg}>{c}</td>" for c in r) + "</tr>"
    return f'<table class="data"><tr>{h}</tr>{body}</table>'


def code(text):
    out = []
    for line in escape(text).split("\n"):
        stripped = line.lstrip(" ")
        pad = "&nbsp;" * (len(line) - len(stripped))
        out.append(pad + stripped)
    return '<div class="code">' + "<br/>".join(out) + "</div>"


def node(cls_color, label, sub):
    return (f'<td align="center" valign="middle" bgcolor="{cls_color}" '
            f'style="color:#ffffff; padding:7px; border-radius:8px; font-size:8.4pt;">'
            f'<b style="color:#ffffff;">{label}</b><br/>'
            f'<span style="color:#dbe6f3; font-size:7.2pt;">{sub}</span></td>')


def arrow():
    return f'<tr><td align="center" style="color:{GRAY}; font-size:13pt;">&#8595;</td></tr>'


DIAGRAM = f"""
<table width="100%" cellspacing="0" cellpadding="0" style="margin:8px 0;">
  <tr><td align="center">
    <table cellspacing="4" cellpadding="0"><tr>{node(ORANGE,'Internet / Navigateurs','HTTPS 443')}</tr></table>
  </td></tr>
  {arrow()}
  <tr><td align="center">
    <table cellspacing="4" cellpadding="0"><tr>
      {node('#334155','Nginx — reverse proxy + TLS','locataire_nginx · 80/443')}
      {node(ORANGE,'Certbot',"Let's Encrypt")}
    </tr></table>
  </td></tr>
  {arrow()}
  <tr><td align="center" bgcolor="#f3f6fb" style="border:1px solid #cbd5e1; padding:8px;">
    <div style="font-size:7.4pt; color:{GRAY}; letter-spacing:1px;">RÉSEAU DOCKER PRIVÉ · locataire_net</div>
    <table cellspacing="4" cellpadding="0"><tr>
      {node(BLUE,'Frontend LCI','locataire_frontend')}
      {node(NAVY,'Backend LCI','locataire_backend · 8000')}
      {node(BLUE,'Frontend Alice','alice_frontend')}
      {node(NAVY,'Backend Alice','alice_backend · 8001')}
    </tr></table>
    <div style="color:{GRAY}; font-size:12pt;">&#8595;</div>
    <table cellspacing="4" cellpadding="0"><tr>
      {node(TEAL,'PostgreSQL 16 — base partagee « lecomptoirimmo »','locataire_postgres · volume postgres_data')}
    </tr></table>
  </td></tr>
</table>
<p class="small">Volumes persistants : <code>postgres_data</code> (base) ·
<code>uploads_data</code> (pièces jointes) · <code>certbot_certs</code> / <code>certbot_www</code> (TLS).
Seul Nginx expose des ports publics ; Postgres n'est jamais exposé.</p>
"""


# ══ DI — DOSSIER D'INSTALLATION ═══════════════════════════════════════════════
DI_BODY = f"""
<h2><span class="num">1</span> Présentation &amp; architecture</h2>
<p class="lead">Installation <b>complète de zéro</b> de la plateforme Le Comptoir Immo
(et de l'application compagnon Alice) sur un serveur neuf.</p>
<p>Deux applications partagent <b>une seule base PostgreSQL</b>, orchestrées par Docker
Compose derrière un reverse-proxy Nginx avec TLS Let's Encrypt.</p>
{DIAGRAM}
{table(["Composant", "Conteneur", "Port", "Domaine public"],
 [["PostgreSQL 16 (base partagée)", "<code>locataire_postgres</code>", "5432 (privé)", "—"],
  ["Backend Le Comptoir Immo", "<code>locataire_backend</code>", "8000", "via Nginx"],
  ["Frontend Le Comptoir Immo", "<code>locataire_frontend</code>", "80", "immo.lecomptoir.services"],
  ["Backend Alice", "<code>alice_backend</code>", "8001", "via Nginx"],
  ["Frontend Alice", "<code>alice_frontend</code>", "80", "alice.lecomptoir.services"],
  ["Reverse-proxy + TLS", "<code>locataire_nginx</code>", "80 / 443", "—"],
  ["Certbot (Let's Encrypt)", "<code>locataire_certbot</code>", "—", "—"]])}
{co("info", "Bon à savoir",
   "Le <b>frontend</b> est compilé au build (<code>vite build</code>) puis servi en statique par Nginx. "
   "Le <b>backend</b> applique au démarrage des <b>migrations légères</b> (colonnes/enums) et "
   "<b>amorce</b> les modèles par défaut + le compte admin initial (~40 s).")}

<h2><span class="num">2</span> Pré-requis serveur</h2>
<ul>
  <li>VPS Linux — référence : <b>OVH AlmaLinux</b>, IP <code>91.134.138.246</code>.</li>
  <li>Accès SSH admin — <code>ssh lecomptoir-vps</code> (port <b>58007</b>, utilisateur
      <code>almalinux</code>, <code>sudo</code> sans mot de passe). Clé privée hors Git.</li>
  <li><b>DNS</b> : A de <code>immo.lecomptoir.services</code> et
      <code>alice.lecomptoir.services</code> → IP du serveur, <b>avant</b> l'émission TLS.</li>
  <li>Pare-feu : ports <b>80</b> et <b>443</b> ouverts.</li>
  <li>Logiciels : <code>git</code>, <code>docker</code> (≥ 24), plugin <code>docker compose</code> v2.</li>
</ul>
<h3>Installation Docker (AlmaLinux / RHEL-like)</h3>
{code('''sudo dnf install -y dnf-plugins-core git
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # puis se reconnecter''')}

<h2><span class="num">3</span> Récupération du code</h2>
{code('''cd ~
git clone git@github.com:service-lecomptoir/LeComptoirImmo.git
cd LeComptoirImmo && git checkout main''')}
{co("warn", "Fichiers d'environnement",
   "Les <code>*.env*</code> sont <b>exclus de Git et des images Docker</b>. "
   "Ils doivent être <b>recréés manuellement</b> à chaque réinstallation (étape 4).")}

<h2><span class="num">4</span> Variables d'environnement</h2>
<p>La prod lit <b>directement</b> les <code>.env.prod</code>. Le conteneur <code>postgres</code>
lit <code>backend/.env</code> (variables <code>POSTGRES_*</code>). Placeholders : <code>&lt;À_RENSEIGNER&gt;</code>.</p>
<h3>backend/.env <span class="badge b-teal">PostgreSQL</span></h3>
{code('''POSTGRES_DB=lecomptoirimmo
POSTGRES_USER=<À_RENSEIGNER>
POSTGRES_PASSWORD=<À_RENSEIGNER>
SECRET_KEY=<À_RENSEIGNER>
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@localhost:5432/lecomptoirimmo''')}
<h3>backend/.env.prod <span class="badge b-navy">Backend LCI</span></h3>
{code('''APP_ENV=production
DEBUG=false
SECRET_KEY=<À_RENSEIGNER>            # ex. openssl rand -hex 32
POSTGRES_HOST=postgres              # nom du service compose
POSTGRES_DB=lecomptoirimmo
POSTGRES_USER=<même que backend/.env>
POSTGRES_PASSWORD=<même que backend/.env>
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@postgres:5432/lecomptoirimmo
CORS_ORIGINS=https://immo.lecomptoir.services
ALICE_URL=http://alice-backend:8001
ALICE_INTERNAL_KEY=<À_RENSEIGNER>   # == INTERNAL_API_KEY d'Alice
SMTP_HOST=                          # vide = e-mails désactivés
SMTP_FROM_EMAIL=noreply@lecomptoir.services
INSEE_API_KEY=                      # IRL auto (vide = saisie manuelle)
FIRST_ADMIN_EMAIL=admin@lecomptoir.services
FIRST_ADMIN_PASSWORD=<À_RENSEIGNER>''')}
<h3>alice/backend/.env.prod <span class="badge b-orange">Backend Alice</span></h3>
{code('''APP_ENV=production
DEBUG=false
SECRET_KEY=<À_RENSEIGNER>           # propre à Alice
DATABASE_URL=postgresql+asyncpg://<USER>:<PASSWORD>@postgres:5432/lecomptoirimmo
INTERNAL_API_KEY=<identique à ALICE_INTERNAL_KEY côté LCI>''')}
{co("danger", "Points de vigilance (causes d'incidents réels)",
   "<ul style='margin:0'>"
   "<li><code>ALICE_INTERNAL_KEY</code> (LCI) <b>==</b> <code>INTERNAL_API_KEY</code> (Alice).</li>"
   "<li>Hôtes = <b>noms de services compose</b> (<code>postgres</code>, <code>alice-backend</code>), pas <code>localhost</code>.</li>"
   "<li>Config <code>extra='forbid'</code> : <b>aucune clé inconnue</b> dans <code>.env.prod</code>, sinon le backend ne démarre pas.</li></ul>")}

<h2><span class="num">5</span> Build &amp; démarrage</h2>
{code('''cd ~/LeComptoirImmo
docker compose -f docker/docker-compose.prod.yml up -d --build
docker compose -f docker/docker-compose.prod.yml ps
docker compose -f docker/docker-compose.prod.yml logs --tail=50 backend''')}

<h2><span class="num">6</span> Certificats TLS (Let's Encrypt)</h2>
<p>DNS doit déjà pointer vers le serveur. Émission initiale :</p>
{code('''docker compose -f docker/docker-compose.prod.yml run --rm certbot \\
  certonly --webroot -w /var/www/certbot \\
  -d immo.lecomptoir.services -d alice.lecomptoir.services \\
  --email <CONTACT_EMAIL> --agree-tos --no-eff-email
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -s reload''')}

<h2><span class="num">7</span> Restauration des données (reprise)</h2>
{code('''# Base
cat dump.sql | docker compose -f docker/docker-compose.prod.yml exec -T postgres \\
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
# Uploads (pièces jointes)
docker run --rm -v lecomptoirimmo_uploads_data:/data -v ~/backups:/backup alpine \\
  sh -c 'tar xzf /backup/uploads_<date>.tgz -C /data' ''')}

<h2><span class="num">8</span> Recette de mise en service</h2>
{code('''curl -s -o /dev/null -w "%{http_code}" https://immo.lecomptoir.services/api/v1/settings/scheduler   # 403
curl -s -o /dev/null -w "%{http_code}" https://immo.lecomptoir.services/    # 200
curl -s -o /dev/null -w "%{http_code}" https://alice.lecomptoir.services/   # 200''')}
{co("tip", "Checklist finale",
   "<ul style='margin:0'>"
   "<li>Backend = 403 / Frontends = 200.</li>"
   "<li>Connexion admin initial (<code>FIRST_ADMIN_*</code>) puis <b>changer le mot de passe</b>.</li>"
   "<li>Aucune erreur dans <code>logs backend</code> / <code>logs alice-backend</code>.</li>"
   "<li>Mettre en place sauvegardes &amp; renouvellement TLS (voir le DE).</li></ul>")}

<h2><span class="num">9</span> Réinstallation de zéro — express</h2>
<ol>
  <li>Provisionner le VPS, installer Docker + git, ouvrir 80/443.</li>
  <li>Pointer les DNS des 2 domaines vers le serveur.</li>
  <li><code>git clone</code> + <code>git checkout main</code>.</li>
  <li>Créer <code>backend/.env</code>, <code>backend/.env.prod</code>, <code>alice/backend/.env.prod</code>.</li>
  <li><code>docker compose ... up -d --build</code>.</li>
  <li>Émettre les certificats TLS puis recharger Nginx.</li>
  <li>(Optionnel) restaurer dump PostgreSQL + volume <code>uploads_data</code>.</li>
  <li>Recette (§8) + changement des mots de passe admin.</li>
</ol>
"""


# ══ DE — DOSSIER D'EXPLOITATION ═══════════════════════════════════════════════
DE_BODY = f"""
<h2><span class="num">1</span> Accès &amp; repères</h2>
<p class="lead">Exploitation courante : surveillance, mises à jour, sauvegardes,
restauration, rollback et dépannage.</p>
{table(["Élément", "Valeur"],
 [["Serveur", "OVH AlmaLinux · IP <code>91.134.138.246</code>"],
  ["Accès SSH", "<code>ssh lecomptoir-vps</code> · port <b>58007</b> · user <code>almalinux</code> · sudo nopasswd"],
  ["Dossier projet", "<code>~/LeComptoirImmo</code>"],
  ["Stack", "<code>docker/docker-compose.prod.yml</code>"],
  ["Domaines", "immo.lecomptoir.services · alice.lecomptoir.services"],
  ["Dépôt", "git@github.com:service-lecomptoir/LeComptoirImmo.git (main)"]])}
<p class="small">Raccourci sur le serveur :
<code>alias dc='docker compose -f docker/docker-compose.prod.yml'</code></p>
{DIAGRAM}

<h2><span class="num">2</span> Surveillance &amp; santé</h2>
{code('''dc ps                        # état (Up / healthy)
dc logs --tail=100 backend   # logs applicatifs
dc stats --no-stream         # CPU / RAM
df -h ; docker system df      # espace disque''')}
{code('''curl -s -o /dev/null -w "%{http_code}" https://immo.lecomptoir.services/api/v1/settings/scheduler  # 403 = OK
curl -s -o /dev/null -w "%{http_code}" https://immo.lecomptoir.services/   # 200
curl -s -o /dev/null -w "%{http_code}" https://alice.lecomptoir.services/  # 200''')}
{co("info", "Lecture des codes",
   "Un <b>403</b> sur <code>/api/v1/settings/scheduler</code> est <b>normal</b> (endpoint protégé) → backend OK. "
   "Un <b>502/504</b> côté Nginx = backend down ou en cours de démarrage.")}

<h2><span class="num">3</span> Mise à jour de l'application</h2>
<h3>Méthode standard (depuis le dépôt)</h3>
{code('''cd ~/LeComptoirImmo
git fetch origin && git checkout main && git pull --ff-only
dc up -d --build backend frontend     # + alice-backend alice-frontend si modifiés
dc ps''')}
{co("warn", "Règles de déploiement",
   "<ul style='margin:0'>"
   "<li>Ne préciser que les <b>services modifiés</b> (évite de recréer Postgres).</li>"
   "<li><b>Éviter</b> <code>--force-recreate</code> : recréer <code>backend</code> recrée <code>postgres</code> → coupure DB.</li>"
   "<li>Après tout changement de <code>.env.prod</code> : <code>up -d --build</code> (un <code>restart</code> ne recharge pas les env_file).</li></ul>")}
<h3>Déploiement « à chaud » depuis Windows (sans Git serveur)</h3>
{code('''$tgz = "$env:TEMP\\leci_deploy.tgz"; if (Test-Path $tgz) { Remove-Item $tgz }
tar --format=ustar -czf $tgz backend/app frontend/src
scp $tgz lecomptoir-vps:~/leci_deploy.tgz
ssh lecomptoir-vps "sudo tar --overwrite -xzf ~/leci_deploy.tgz -C ~/LeComptoirImmo && sudo chown -R almalinux:almalinux ~/LeComptoirImmo/backend/app ~/LeComptoirImmo/frontend/src"
ssh lecomptoir-vps "cd ~/LeComptoirImmo && docker compose -f docker/docker-compose.prod.yml up -d --build backend frontend"''')}
<p class="small">Format <b>ustar</b> (en-têtes compatibles) ; extraction <code>sudo</code> + <code>chown</code>
pour les dossiers en lecture seule. Pas de cmdlets PowerShell dans la commande <code>ssh</code>.</p>

<h2><span class="num">4</span> Rollback / bascule (retour arrière)</h2>
{co("danger", "Avant tout rollback", "Faire une <b>sauvegarde DB</b> (§5). Un retour de code ne "
   "défait pas une migration de données déjà appliquée.")}
<h3>Rollback du code</h3>
{code('''cd ~/LeComptoirImmo
git fetch origin && git log --oneline -10      # repérer le dernier commit stable <SHA>
git checkout <SHA>                             # (après sauvegarde)
dc up -d --build backend frontend alice-backend alice-frontend''')}
<p>Puis revenir à la branche : <code>git checkout main &amp;&amp; git pull --ff-only</code>.</p>
<h3>Rollback d'image (sans rebuild)</h3>
{code('''docker images | grep docker-backend     # repérer un Image ID antérieur
docker tag <IMAGE_ID> docker-backend:latest
dc up -d backend''')}
<h3>Restauration base (rollback données)</h3>
{code('''dc stop backend alice-backend
cat ~/backups/leci_<date>.sql | dc exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
dc start backend alice-backend''')}

<h2><span class="num">5</span> Sauvegardes</h2>
{code('''mkdir -p ~/backups
# Base
dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > ~/backups/leci_$(date +%F).sql
# Uploads
docker run --rm -v lecomptoirimmo_uploads_data:/data -v ~/backups:/backup alpine \\
  tar czf /backup/uploads_$(date +%F).tgz -C /data .''')}
{co("tip", "Bonnes pratiques",
   "Copier <code>~/backups/</code> hors-serveur régulièrement. <b>Tester une restauration</b> "
   "périodiquement. Vérifier le préfixe de volume avec <code>docker volume ls</code>.")}

<h2><span class="num">6</span> Automatisation (cron)</h2>
<p>Éditer la crontab : <code>crontab -e</code></p>
{code('''# Sauvegarde DB quotidienne — 02h30
30 2 * * * cd ~/LeComptoirImmo && docker compose -f docker/docker-compose.prod.yml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > ~/backups/leci_$(date +\\%F).sql 2>> ~/backups/backup.log
# Sauvegarde uploads — 02h45
45 2 * * * docker run --rm -v lecomptoirimmo_uploads_data:/data -v ~/backups:/backup alpine tar czf /backup/uploads_$(date +\\%F).tgz -C /data . 2>> ~/backups/backup.log
# Purge > 30 jours — 03h15
15 3 * * * find ~/backups -name 'leci_*.sql' -mtime +30 -delete ; find ~/backups -name 'uploads_*.tgz' -mtime +30 -delete
# Renouvellement TLS — 1er du mois 04h00
0 4 1 * * cd ~/LeComptoirImmo && docker compose -f docker/docker-compose.prod.yml run --rm certbot renew && docker compose -f docker/docker-compose.prod.yml exec nginx nginx -s reload''')}
{co("info", "Échappement cron", "Dans une crontab, <code>%</code> doit être échappé en <code>\\%</code> "
   "(cf. <code>date +%F</code> ci-dessus).")}

<h2><span class="num">7</span> Conteneurs &amp; TLS</h2>
{table(["Commande", "Effet"],
 [["<code>dc restart backend</code>", "Redémarrage simple (ne recharge pas les env_file)"],
  ["<code>dc up -d --build backend</code>", "Rebuild + recréation (recharge .env.prod)"],
  ["<code>dc stop</code> / <code>dc start</code>", "Arrêt / démarrage de la stack"],
  ["<code>dc down</code>", "Supprime les conteneurs — <b>volumes CONSERVÉS</b>"],
  ["<code>dc run --rm certbot renew</code>", "Renouvelle les certificats TLS"]])}
{co("danger", "Ne jamais", "Utiliser <code>dc down -v</code> en production : cela "
   "<b>efface la base et les uploads</b>. Ni <code>docker volume prune</code> à l'aveugle.")}

<h2><span class="num">8</span> Rôles &amp; isolation</h2>
<p>Rôles : <span class="badge b-navy">admin</span> <span class="badge b-blue">gestionnaire</span>
<span class="badge b-teal">GP</span> <span class="badge b-orange">propriétaire</span>
<span class="badge b-gray">locataire</span>.</p>
{co("tip", "Isolation appliquée (listes ET accès par identifiant)",
   "Un <b>GP</b> ne voit que ses ressources ; un <b>mandataire</b> ne voit pas celles d'un GP ; "
   "<b>propriétaire</b>/<b>locataire</b> limités à leur périmètre. Vérifié sur paiements, avis, "
   "documents, biens, locataires et fiches propriétaires (lecture + écriture + téléchargements).")}

<h2><span class="num">9</span> E-mails (SMTP)</h2>
<p>L'envoi est <b>désactivé tant que <code>SMTP_HOST</code> est vide</b> : les documents restent
consultables dans l'app, aucun e-mail ne part. Pour activer : renseigner <code>SMTP_*</code> dans
<code>backend/.env.prod</code> puis <code>dc up -d --build backend</code>.</p>

<h2><span class="num">10</span> Dépannage rapide (FAQ)</h2>
{table(["Symptôme", "Cause probable", "Action"],
 [["<code>502/504</code>", "Backend down / démarrage / crash", "<code>dc ps</code> ; <code>dc logs --tail=100 backend</code>"],
  ["Backend ne démarre pas", "Clé inconnue dans <code>.env.prod</code>", "Corriger ; <code>dc up -d --build backend</code>"],
  ["Alice <code>unhealthy</code>", "Postgres recréé (dépendance)", "<code>dc up -d alice-backend</code>"],
  ["Liaison LCI ↔ Alice KO", "Clés internes différentes", "Aligner ; rebuild des 2 backends"],
  ["Modif <code>.env.prod</code> sans effet", "<code>restart</code> ne recharge pas", "<code>dc up -d --build &lt;service&gt;</code>"],
  ["Disque plein", "Images orphelines", "<code>docker image prune -f</code>"],
  ["Certificat expiré", "Renouvellement non fait", "<code>certbot renew</code> + reload Nginx"],
  ["Quittance non reçue", "SMTP désactivé", "Activer SMTP (§9)"]])}
<h3>Redémarrage propre (incident généralisé)</h3>
{code('''cd ~/LeComptoirImmo
dc logs --tail=200 backend alice-backend
dc up -d                                   # recrée les conteneurs manquants (volumes intacts)
dc up -d --build backend frontend alice-backend alice-frontend   # si besoin''')}

<h2><span class="num">11</span> Bonnes pratiques</h2>
<ul>
  <li>Sauvegarde DB quotidienne + <b>test de restauration</b> périodique.</li>
  <li>Déployer <b>service par service</b>, vérifier la santé après chaque déploiement.</li>
  <li>Ne jamais committer de secret ; <code>*.env.prod</code> dans le coffre de l'équipe.</li>
  <li>Garder Postgres hors d'accès public.</li>
  <li>Documenter chaque incident et sa résolution.</li>
</ul>
"""


# ══ DC — AGENT IA WHATSAPP ════════════════════════════════════════════════════
WA_DIAGRAM = f"""
<table width="100%" cellspacing="0" cellpadding="0" style="margin:8px 0;">
  <tr><td align="center">
    <table cellspacing="4" cellpadding="0"><tr>
      {node('#25D366','WhatsApp — gestionnaire','messages &amp; rappels')}
    </tr></table>
  </td></tr>
  {arrow()}
  <tr><td align="center" bgcolor="#f3f6fb" style="border:1px solid #cbd5e1; padding:8px;">
    <div style="font-size:7.4pt; color:{GRAY}; letter-spacing:1px;">LE COMPTOIR IMMO — BACKEND</div>
    <table cellspacing="4" cellpadding="0"><tr>
      {node(NAVY,'Webhook entrant','/webhooks/whatsapp')}
      {node(TEAL,'Agent IA (Claude)','outils = endpoints')}
      {node(ORANGE,'Scheduler','rappels proactifs')}
    </tr></table>
    <div style="color:{GRAY}; font-size:12pt;">&#8595;</div>
    <table cellspacing="4" cellpadding="0"><tr>
      {node(BLUE,'Endpoints metier','paiements · quittances · demarches · entretiens · scoring · baux')}
    </tr></table>
  </td></tr>
  {arrow()}
  <tr><td align="center"><table cellspacing="4" cellpadding="0"><tr>
    {node('#334155','Fournisseur WhatsApp','Meta Cloud API')}
  </tr></table></td></tr>
</table>
<p class="small">Liaison numéro ↔ gestionnaire (opt-in, vérification, préférences) + journal d'audit.
L'agent applique le même périmètre que l'app (isolation par rôle).</p>
"""

DC_BODY = f"""
<h2><span class="num">1</span> Objectifs</h2>
<p class="lead">Un <b>agent conversationnel</b> qui contacte les gestionnaires sur <b>WhatsApp</b>
pour leur envoyer des <b>rappels</b>, répondre à leurs <b>questions</b> et <b>exécuter des instructions</b>
via l'API Le Comptoir Immo.</p>
<ul>
  <li><b>Gagner du temps</b> : être notifié et agir sans ouvrir l'app.</li>
  <li><b>Proactivité</b> : échéances, impayés, maintenances dues, démarches en attente, baux à renouveler.</li>
  <li><b>Conversation naturelle</b> : poser une question ou donner une instruction.</li>
  <li><b>Réutiliser l'existant</b> : l'app porte déjà tout le métier ; l'agent ne fait qu'<b>orchestrer</b>.</li>
</ul>
{co("info", "Hors périmètre v1",
   "Pas de WhatsApp avec locataires/propriétaires (gestionnaires seulement). "
   "Pas de pièces sensibles sur WhatsApp — lien vers l'app pour le détail.")}

<h2><span class="num">2</span> Architecture cible</h2>
{WA_DIAGRAM}

<h2><span class="num">3</span> Le canal WhatsApp (contraintes)</h2>
{table(["Contrainte", "Conséquence de conception"],
 [["Numéro WhatsApp Business + vérification Meta", "À provisionner avant tout développement"],
  ["Templates pré-approuvés (HSM) pour l'envoi proactif", "Les rappels passent par un catalogue de templates validés"],
  ["Fenêtre de service 24 h", "Hors fenêtre → relance via template"],
  ["Opt-in explicite", "Étape d'activation + consentement enregistré"],
  ["Facturation par conversation", "Budgéter ; limiter aux rappels pertinents"]])}
{co("tip", "Alternative / démarrage rapide",
   "Le même agent peut démarrer par <b>e-mail</b> ou <b>chat intégré à l'app</b> (sans dépendance Meta), "
   "puis WhatsApp en surcouche.")}

<h2><span class="num">4</span> Modèle de données</h2>
<p><b>manager_whatsapp_link</b> : <code>user_id</code>, <code>phone_e164</code>, <code>opt_in_at</code>,
<code>opt_out_at</code>, <code>verify_code/verified_at</code>, <code>prefs</code> (JSONB), <code>last_inbound_at</code>.</p>
<p><b>whatsapp_message_log</b> (audit + idempotence) : <code>direction</code>, <code>template_name</code>,
<code>body_excerpt</code>, <code>status</code>, <code>provider_id</code>, <code>created_at</code>.</p>
{co("warn", "Minimisation", "On stocke des extraits non sensibles et des identifiants techniques, pas de PII détaillée.")}

<h2><span class="num">5</span> L'agent IA (orchestration)</h2>
<p>Modèle Claude + <b>jeu d'outils</b> = sous-ensemble contrôlé des endpoints. L'agent reçoit l'identité
du gestionnaire → <b>isolation respectée</b>. Actions modifiantes → <b>récapitulatif + confirmation</b> + journalisation.</p>
{table(["Intention", "Outil (endpoint)"],
 [["« quels loyers manquent ce mois ? »", "Paiements en retard (lecture)"],
  ["« score de M. X ? »", "/scoring/{tenant} (lecture)"],
  ["« envoie la quittance de mai à M. X »", "/payments/{id}/quittance/send (action + confirmation)"],
  ["« marque le loyer d'avril payé »", "/payments/{id}/record (action + confirmation)"],
  ["« planifie une révision chaudière chez Y »", "Création d'entretien (action + confirmation)"]])}

<h2><span class="num">6</span> Catalogue de rappels proactifs</h2>
{table(["Rappel", "Source existante", "Fréquence"],
 [["Loyers en retard", "Paiements en retard", "Quotidien"],
  ["Échéances à venir", "Avis d'échéance", "Hebdomadaire"],
  ["Mauvais payeurs / risque", "Scoring (note D/E)", "Hebdomadaire"],
  ["Maintenances dues", "Entretiens / autoplan", "Hebdomadaire"],
  ["Démarches en attente", "Module Démarche", "Quotidien si en retard"],
  ["Baux à renouveler", "Dates de fin de bail", "Mensuel"]])}
<p class="small">Chaque rappel = un template approuvé (texte sobre + variables) renvoyant vers l'app pour le détail.</p>

<h2><span class="num">7</span> Sécurité, RGPD &amp; gouvernance</h2>
<ul>
  <li><b>Consentement</b> : opt-in explicite, opt-out (« STOP ») à tout moment.</li>
  <li><b>Minimisation</b> : pas de RIB / n° sécu / détail financier complet sur WhatsApp ; lien vers l'app.</li>
  <li><b>Authentification</b> : numéro rattaché à un compte vérifié (code unique), jeton de liaison.</li>
  <li><b>Confirmation</b> des actions modifiantes + <b>journal d'audit</b>.</li>
  <li><b>Technique</b> : vérification de signature du webhook, secrets en .env.prod, rate-limiting.</li>
  <li><b>Isolation rôle</b> : même périmètre que l'app (mandataire hors GP, GP = son périmètre).</li>
</ul>

<h2><span class="num">8</span> Configuration (.env.prod)</h2>
{code('''WHATSAPP_PROVIDER=meta            # meta | twilio | 360dialog
WHATSAPP_PHONE_NUMBER_ID=<À_RENSEIGNER>
WHATSAPP_BUSINESS_ACCOUNT_ID=<À_RENSEIGNER>
WHATSAPP_TOKEN=<À_RENSEIGNER>          # jeton d'acces (long-lived)
WHATSAPP_VERIFY_TOKEN=<À_RENSEIGNER>   # verification du webhook
WHATSAPP_APP_SECRET=<À_RENSEIGNER>     # signature des requetes entrantes
AGENT_LLM_API_KEY=<À_RENSEIGNER>       # cle du modele IA''')}

<h2><span class="num">9</span> Plan de livraison par phases</h2>
<h3>Phase 1 — Rappels sortants (faible risque)</h3>
<p>Numéro + compte Meta, 3-4 templates approuvés, table de liaison + opt-in, scheduler → 2-3 rappels
(loyers en retard, maintenances dues, démarches en attente). <b>Recette</b> : opt-in reçoit le rappel, opt-out OK.</p>
<h3>Phase 2 — Agent en lecture</h3>
<p>Webhook entrant + identification + agent <b>lecture seule</b> (paiements, scoring, démarches).
<b>Recette</b> : réponses correctes, périmètre respecté, hors-droits refusé.</p>
<h3>Phase 3 — Prise d'instructions</h3>
<p>Outils modifiants avec <b>confirmation</b> + journalisation. <b>Recette</b> : action seulement après
confirmation, trace d'audit, isolation vérifiée.</p>

<h2><span class="num">10</span> Estimation &amp; risques</h2>
{co("danger", "Risque principal",
   "Fuite de données sensibles via un canal grand public → mitigé par la minimisation (§7). "
   "Dépendance externe : validation Meta (numéro, templates) = délai non maîtrisé en interne.")}
<ul>
  <li><b>Effort</b> : Phase 1 modérée ; Phases 2-3 plus lourdes (agent + sécurité).</li>
  <li><b>Coût récurrent</b> : facturation Meta par conversation + coût du modèle IA.</li>
  <li><b>Alternative</b> : agent e-mail / chat in-app pour valider l'usage avant WhatsApp.</li>
</ul>

<h2><span class="num">11</span> Décisions à prendre</h2>
<ol>
  <li><b>Fournisseur</b> : Meta Cloud API direct, ou Twilio / 360dialog ?</li>
  <li><b>Canal de démarrage</b> : WhatsApp d'emblée, ou e-mail / in-app d'abord ?</li>
  <li><b>Périmètre Phase 1</b> : quels 3 rappels prioritaires ?</li>
  <li><b>Modèle IA</b> : quel fournisseur / budget ?</li>
  <li><b>Politique d'actions</b> : jusqu'où autoriser les actions modifiantes par message ?</li>
</ol>
"""


def build(title_header, cover_html, body_html):
    return (f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
            f"{footer()}{cover_html}{body_html}</body></html>")


def render(html, out):
    with open(out, "wb") as f:
        res = pisa.CreatePDF(html, dest=f, encoding="utf-8")
    if res.err:
        raise SystemExit(f"Erreur pisa sur {out}")
    print("PDF écrit :", out)


def main():
    render(build("DI", cover("Dossier d'Installation",
                             "Réinstallation de zéro · déploiement", "DI · Support / Exploitation"),
                 DI_BODY), os.path.join(HERE, "DI_Dossier_Installation.pdf"))
    render(build("DE", cover("Dossier d'Exploitation",
                             "Surveillance · mises à jour · sauvegardes · dépannage", "DE · Support / Exploitation"),
                 DE_BODY), os.path.join(HERE, "DE_Dossier_Exploitation.pdf"))
    render(build("DC", cover("Agent IA WhatsApp",
                             "Rappels · questions · prise d'instructions pour les gestionnaires",
                             "DC · Dossier de conception"),
                 DC_BODY), os.path.join(HERE, "DC_Agent_WhatsApp.pdf"))


if __name__ == "__main__":
    main()
