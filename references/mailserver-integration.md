# Docker Mailserver — Autonomyx LLM Gateway

## Role

Self-hosted SMTP server on Coolify. Used by:
- **Lago** — invoice delivery, payment reminders
- **Keycloak** — account verification, password reset emails

Sender domain: `openautonomyx.com`
Billing sender: `billing@openautonomyx.com`

---

## docker-compose addition (append to Coolify stack)

```yaml
  mailserver:
    image: ghcr.io/docker-mailserver/docker-mailserver:latest
    container_name: autonomyx-mailserver
    hostname: mail.openautonomyx.com
    restart: always
    networks:
      - coolify
    ports:
      - "25:25"       # SMTP (inbound + relay)
      - "465:465"     # SMTPS
      - "587:587"     # Submission (used by Lago + Keycloak)
      - "993:993"     # IMAPS (optional)
    environment:
      - ENABLE_RSPAMD=1
      - ENABLE_CLAMAV=0
      - ENABLE_FAIL2BAN=1
      - POSTFIX_INET_PROTOCOLS=ipv4
      - SSL_TYPE=letsencrypt
      - PERMIT_DOCKER=network
      - POSTMASTER_ADDRESS=admin@openautonomyx.com
    volumes:
      - mailserver-data:/var/mail
      - mailserver-state:/var/mail-state
      - mailserver-logs:/var/log/mail
      - mailserver-config:/tmp/docker-mailserver
      - /etc/letsencrypt:/etc/letsencrypt:ro   # shared with Traefik
    cap_add:
      - NET_ADMIN
    labels:
      - "traefik.enable=false"   # mailserver handles its own TLS
```

Add to `volumes:` block:
```yaml
  mailserver-data:
  mailserver-state:
  mailserver-logs:
  mailserver-config:
```

---

## Initial Setup (run once after first deploy)

```bash
# 1. Create billing mailbox
docker exec autonomyx-mailserver setup email add billing@openautonomyx.com YOUR_MAIL_PASSWORD

# 2. Create DKIM key (do this BEFORE setting DNS)
docker exec autonomyx-mailserver setup config dkim

# 3. View DKIM public key to add to DNS
docker exec autonomyx-mailserver cat /tmp/docker-mailserver/opendkim/keys/openautonomyx.com/mail.txt
```

---

## DNS Records Required

Add these to openautonomyx.com DNS (Cloudflare or your registrar):

| Type | Name | Value |
|---|---|---|
| A | mail | `51.75.251.56` (VPS IP) |
| MX | @ | `mail.openautonomyx.com` (priority 10) |
| TXT | @ | `v=spf1 mx a:mail.openautonomyx.com ~all` |
| TXT | mail._domainkey | DKIM value from setup step above |
| TXT | _dmarc | `v=DMARC1; p=quarantine; rua=mailto:admin@openautonomyx.com` |

---

## SMTP credentials for Lago + Keycloak

```
SMTP_HOST=mailserver        # Docker service name (internal network)
SMTP_PORT=587
SMTP_USERNAME=billing@openautonomyx.com
SMTP_PASSWORD=YOUR_MAIL_PASSWORD_HERE
SMTP_TLS=starttls
SMTP_FROM=billing@openautonomyx.com
```

---

## Env vars (add to .env.example)

```
# Docker Mailserver
MAIL_PASSWORD=YOUR_MAIL_PASSWORD_HERE
SMTP_HOST=mailserver
SMTP_PORT=587
SMTP_USERNAME=billing@openautonomyx.com
SMTP_PASSWORD=YOUR_MAIL_PASSWORD_HERE
SMTP_FROM=billing@openautonomyx.com
```

---

## Wire Lago → Mailserver

In Lago docker-compose environment block:
```yaml
  lago-api:
    environment:
      - LAGO_FROM_EMAIL=billing@openautonomyx.com
      - LAGO_SMTP_ADDRESS=mailserver
      - LAGO_SMTP_PORT=587
      - LAGO_SMTP_USERNAME=billing@openautonomyx.com
      - LAGO_SMTP_PASSWORD=${MAIL_PASSWORD}
      - LAGO_SMTP_AUTH_METHOD=plain
      - LAGO_SMTP_ENABLE_STARTTLS_AUTO=true
```

## Wire Keycloak → Mailserver

In Keycloak: Realm Settings → Email → configure:
- Host: `mailserver`
- Port: `587`
- From: `billing@openautonomyx.com`
- Enable StartTLS: on
- Username: `billing@openautonomyx.com`
- Password: `${MAIL_PASSWORD}`

Or via Keycloak admin API:
```bash
curl -X PUT https://auth.openautonomyx.com/admin/realms/autonomyx \
  -H "Authorization: Bearer $KC_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "smtpServer": {
      "host": "mailserver",
      "port": "587",
      "from": "billing@openautonomyx.com",
      "fromDisplayName": "Autonomyx Billing",
      "auth": "true",
      "user": "billing@openautonomyx.com",
      "password": "'$MAIL_PASSWORD'",
      "starttls": "true"
    }
  }'
```

---

## Verify mail delivery

```bash
# Send test email from mailserver container
docker exec autonomyx-mailserver bash -c \
  "echo 'Test' | mail -s 'LLM Gateway Mail Test' billing@openautonomyx.com"

# Check Lago invoice email (trigger from Lago UI: Customer → Invoice → Send)

# Check mail logs
docker logs autonomyx-mailserver --tail 50
```
