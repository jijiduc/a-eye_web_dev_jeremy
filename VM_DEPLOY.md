# A-eye VM Deployment

## 1. Prerequisites

- Ubuntu Server 24.04 VM reachable as `jaime.barranco@vlenpaeye.hevs.ch`
- DNS `aeye.hevs.ch` pointing to the VM, currently as `aeye.hevs.ch CNAME vlenpaeye.hevs.ch`
- Inbound `443/tcp` open from the internet
- Outbound HTTPS allowed for Docker Hub, GitHub, Auth0, and Let's Encrypt
- Outbound SSH from the VM to:
  - `10.130.2.72:22`
  - `10.130.2.68:22`
- SMB access from the VM to `filer01.hevs.ch`

## 2. Install Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl git gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
newgrp docker
```

## 3. Clone the repo

```bash
mkdir -p ~/apps
cd ~/apps
git clone --branch vm --single-branch https://github.com/jaimebarran/a-eye_web.git
cd a-eye_web
```

If the repo was cloned earlier with a different single branch:

```bash
git remote set-branches origin '*'
git fetch origin
git switch vm
git pull --ff-only
```

## 4. Mount filer01

```bash
sudo apt install -y cifs-utils
sudo mkdir -p /mnt/FS_PROJETS
sudo mount -t cifs //filer01.hevs.ch/FS_PROJETS /mnt/FS_PROJETS \
  -o username=jaime.barranco,uid=$(id -u),gid=$(id -g),vers=3.0
```

The app expects this host path:

```text
/mnt/FS_PROJETS/MatTechLab/jaime.barranco/A-eye/A-eye_web/data
```

## 5. SSH key for HPC

The app uses the VM key directory mounted into the container as `/root/.ssh`.

```bash
mkdir -p '/home/jaime.barranco@hevs.ch/.ssh'
chmod 700 '/home/jaime.barranco@hevs.ch/.ssh'
```

Generate a dedicated key if it does not exist yet:

```bash
ssh-keygen -t ed25519 -f '/home/jaime.barranco@hevs.ch/.ssh/id_ed25519' -C 'aeye-vm@vlenpaeye' -N ''
```

Ask for the public key to be added to `authorized_keys` on Chacha and Disco:

```bash
cat '/home/jaime.barranco@hevs.ch/.ssh/id_ed25519.pub'
```

Create SSH config:

```bash
cat > '/home/jaime.barranco@hevs.ch/.ssh/config' <<'EOF'
Host chacha
    HostName 10.130.2.72
    User jaime.barrancohernandez
    IdentityFile /root/.ssh/id_ed25519
    IdentitiesOnly yes

Host disco
    HostName 10.130.2.68
    User jaime.barrancohernandez
    IdentityFile /root/.ssh/id_ed25519
    IdentitiesOnly yes

Host 10.130.2.72
    User jaime.barrancohernandez
    IdentityFile /root/.ssh/id_ed25519
    IdentitiesOnly yes

Host 10.130.2.68
    User jaime.barrancohernandez
    IdentityFile /root/.ssh/id_ed25519
    IdentitiesOnly yes
EOF

chmod 600 '/home/jaime.barranco@hevs.ch/.ssh/config'
chmod 600 '/home/jaime.barranco@hevs.ch/.ssh/id_ed25519'
chmod 644 '/home/jaime.barranco@hevs.ch/.ssh/id_ed25519.pub'
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
A_EYE_SSH_DIR_PROD=/home/jaime.barranco@hevs.ch/.ssh

MAIL_SERVER=mail.hevs.ch
MAIL_PORT=25
MAIL_USE_TLS=False
MAIL_USE_SSL=False
MAIL_DEFAULT_SENDER=noreply@hevs.ch
```

## 7. Traefik ACME storage

Traefik uses TLS-ALPN challenge on `443/tcp`, so `80/tcp` is not required.

```bash
sudo mkdir -p /letsencrypt
sudo touch /letsencrypt/acme.json
sudo chmod 600 /letsencrypt/acme.json
```

## 8. Start the VM stack

```bash
docker compose -f docker-compose.vm.yml up -d --build
```

## 9. Install systemd unit

```bash
sudo cp services/aeyeweb.service /etc/systemd/system/aeyeweb.service
sudo systemctl daemon-reload
sudo systemctl enable --now aeyeweb.service
```

Traefik renews Let's Encrypt certificates automatically, so the old certbot renewal timer is not needed for the VM deployment.

## 10. Verify

```bash
docker compose -f docker-compose.vm.yml ps
docker compose -f docker-compose.vm.yml logs traefik
docker compose -f docker-compose.vm.yml logs flask_app
curl -Ik https://aeye.hevs.ch
```

## 11. Auth0 production settings

- Allowed Callback URLs:
  - `https://aeye.hevs.ch/callback`
- Allowed Logout URLs:
  - `https://aeye.hevs.ch/`
- Allowed Web Origins:
  - `https://aeye.hevs.ch`
