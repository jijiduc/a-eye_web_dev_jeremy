# A-eye VM Deployment

## 1. Prerequisites

- Ubuntu Server 24.04 VM reachable as `jaime.barranco@vlenpaeye.hevs.ch`
- DNS `aeye.hevs.ch` pointing to the VM public IP
- Ports `80/tcp` and `443/tcp` open to the internet
- Outbound SSH from the VM to:
  - `10.130.2.72:22`
  - `10.130.2.68:22`
- Host mount for `filer01` available at:
  - `/mnt/filer01/MatTechLab/jaime.barranco/A-eye/A-eye_web/data`

## 2. Install Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
newgrp docker
```

## 3. Clone the repo

```bash
mkdir -p ~/apps
cd ~/apps
git clone <YOUR-REPO-URL> a-eye_web
cd a-eye_web
```

## 4. Create runtime directories

```bash
sudo mkdir -p /etc/aeye/ssh
sudo mkdir -p /var/www/certbot
sudo mkdir -p /etc/letsencrypt
mkdir -p logs data static/upload
```

## 5. Install the app SSH key

Use a dedicated deploy key, not a personal workstation key.

```bash
sudo cp /path/to/id_ed25519 /etc/aeye/ssh/id_ed25519
sudo cp /path/to/known_hosts /etc/aeye/ssh/known_hosts
sudo chmod 700 /etc/aeye/ssh
sudo chmod 600 /etc/aeye/ssh/id_ed25519
sudo chmod 644 /etc/aeye/ssh/known_hosts
```

If needed, populate `known_hosts`:

```bash
ssh-keyscan 10.130.2.72 | sudo tee -a /etc/aeye/ssh/known_hosts
ssh-keyscan 10.130.2.68 | sudo tee -a /etc/aeye/ssh/known_hosts
```

## 6. Create `.env`

```env
AUTH0_DOMAIN=dev-efo7i5wwqsmfsqvt.eu.auth0.com
AUTH0_CLIENT_ID=...
AUTH0_CLIENT_SECRET=...
AUTH0_AUDIENCE=https://dev-efo7i5wwqsmfsqvt.eu.auth0.com/api/v2/
AUTH0_CALLBACK_URL=https://aeye.hevs.ch/callback
AUTH0_LOGOUT_URL=https://aeye.hevs.ch/
AUTH0_CALLBACK_URL_PROD=https://aeye.hevs.ch/callback
AUTH0_LOGOUT_URL_PROD=https://aeye.hevs.ch/

SECRET_KEY=...
A_EYE_SSH_DIR_PROD=/etc/aeye/ssh

MAIL_SERVER=mail.hevs.ch
MAIL_PORT=25
MAIL_USE_TLS=False
MAIL_USE_SSL=False
MAIL_DEFAULT_SENDER=noreply@hevs.ch
```

## 7. First certificate issuance

Start the stack without HTTPS first if needed, or ensure DNS already resolves to the VM.

```bash
docker compose -f docker-compose.vm.yml up -d --build nginx flask_app
docker compose -f docker-compose.vm.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d aeye.hevs.ch \
  --email jaime.barrancohernandez@hevs.ch \
  --agree-tos \
  --no-eff-email
docker compose -f docker-compose.vm.yml restart nginx
```

## 8. Install systemd units

```bash
sudo cp services/aeyeweb.service /etc/systemd/system/aeyeweb.service
sudo cp services/aeyeweb-certbot-renew.service /etc/systemd/system/aeyeweb-certbot-renew.service
sudo cp services/aeyeweb-certbot-renew.timer /etc/systemd/system/aeyeweb-certbot-renew.timer
sudo systemctl daemon-reload
sudo systemctl enable --now aeyeweb.service
sudo systemctl enable --now aeyeweb-certbot-renew.timer
```

## 9. Verify

```bash
docker compose -f docker-compose.vm.yml ps
docker compose -f docker-compose.vm.yml logs nginx
docker compose -f docker-compose.vm.yml logs flask_app
curl -I http://aeye.hevs.ch
curl -I https://aeye.hevs.ch
```

## 10. Auth0 production settings

- Allowed Callback URLs:
  - `https://aeye.hevs.ch/callback`
- Allowed Logout URLs:
  - `https://aeye.hevs.ch/`
- Allowed Web Origins:
  - `https://aeye.hevs.ch`
