# Deploying PlanetWatch

One Ubuntu server runs everything: the citizen website, the municipal dashboard, the API,
the app downloads and the YOLO model. The app uses SQLite, and uploaded photos stay on the server's disk.

```
phone / browser ──https──> nginx (Let's Encrypt) ──> gunicorn :8000 ──> Flask app + YOLO (CPU)
                                                                        ├─ backend/instance/reports.db
                                                                        └─ backend/uploads/
```

| File | Purpose |
| --- | --- |
| `setup.sh` | One-time server setup: packages, CPU PyTorch, `.env`, service, nginx, https |
| `update.sh` | Pull the latest code from GitHub and restart |
| `planetwatch.service` | systemd service (gunicorn, 1 process × 4 threads) |
| `nginx.conf` | Reverse proxy, 80 MB uploads, 5-minute timeout |
| `env.production.example` | Template for the server's `.env` |

## 1. Create the server (Azure for Students)

In <https://portal.azure.com>, go to **Virtual machines → Create → Azure virtual machine**:

| Setting | Value |
| --- | --- |
| Subscription | Azure for Students |
| Resource group | Create new: `planetwatch` |
| Virtual machine name | `planetwatch` |
| Region | **(Africa) South Africa North**. If the student policy refuses it, pick any region it allows |
| Image | Ubuntu Server 24.04 LTS - x64 Gen2 |
| Size | **Standard_B2s** (2 vCPUs, 4 GiB). PyTorch needs the 4 GiB |
| Authentication | SSH public key, username `azureuser`, key pair name `planetwatch_key` |
| Inbound ports | SSH (22), HTTP (80), HTTPS (443) |

Then click **Review + create → Create** and **Download private key**. Save it as
`Downloads\planetwatch_key.pem`.

When the VM is ready, open it and go to **Overview → DNS name → Not configured**. Set a DNS
name label such as `planetwatch-zw` and save. Your address is now
`planetwatch-zw.southafricanorth.cloudapp.azure.com` (with your own region). You don't need to buy a domain.

> **Cost:** B2s uses roughly $30 of the $100 credit per month. When nobody needs the
> site, **Stop** the VM in the portal so it stops using credit.

## 2. Install PlanetWatch on it

Run this in PowerShell on your PC. The first line makes Windows accept the key file:

```powershell
icacls "$HOME\Downloads\planetwatch_key.pem" /inheritance:r /grant:r "$($env:USERNAME):R"
ssh -i "$HOME\Downloads\planetwatch_key.pem" azureuser@planetwatch-zw.southafricanorth.cloudapp.azure.com
```

Then run these on the server, replacing the address and email with yours:

```bash
sudo git clone https://github.com/Presley-16/Vision_Based_Waste_Detection.git /opt/planetwatch
sudo bash /opt/planetwatch/deploy/setup.sh planetwatch-zw.southafricanorth.cloudapp.azure.com you@example.com
```

Setup takes about 10 minutes, most of it installing PyTorch. At the end it prints the
**municipal dashboard password**. Write it down; it is also stored in `/opt/planetwatch/.env`.

## 3. Upload the model (and the Android app)

The weights and the APK aren't in git. Run this from the project folder on your PC:

```powershell
$key = "$HOME\Downloads\planetwatch_key.pem"; $srv = "azureuser@planetwatch-zw.southafricanorth.cloudapp.azure.com"
scp -i $key model\weights\best.pt "${srv}:/tmp/best.pt"
scp -i $key mobile\dist\PlanetWatch.apk "${srv}:/tmp/PlanetWatch.apk"   # once rebuilt (step 5)
```

Then run this on the server:

```bash
sudo mv /tmp/best.pt /opt/planetwatch/model/weights/best.pt
sudo mv /tmp/PlanetWatch.apk /opt/planetwatch/mobile/dist/PlanetWatch.apk
sudo chown -R planetwatch: /opt/planetwatch/model/weights /opt/planetwatch/mobile/dist
sudo systemctl restart planetwatch
```

Open `https://<your address>` to see the website. The dashboard is at `/municipal/`.

## 4. Settings

`sudo nano /opt/planetwatch/.env`, then `sudo systemctl restart planetwatch`. Use it to:

- set `YOLO_CONF_THRESHOLD` to the value chosen from `python -m model.evaluate --sweep`.
- copy the email/SMS alert values from your local `.env` to switch alerts on.

## 5. Point the mobile apps at the server

The apps are built with the server address baked in, so rebuild them once:

```powershell
cd mobile
npm run build:android -- https://planetwatch-zw.southafricanorth.cloudapp.azure.com
```

For iOS, run the **iOS app** GitHub Action with `server_url` set to the same https address.
Then upload the new `PlanetWatch.apk` (step 3).

## Day-to-day

| Task | Command (on the server) |
| --- | --- |
| Deploy new code after `git push` | `sudo bash /opt/planetwatch/deploy/update.sh` |
| Live logs | `sudo journalctl -u planetwatch -f` |
| Restart | `sudo systemctl restart planetwatch` |
| Back up reports + photos | `sudo tar czf ~/planetwatch-backup-$(date +%F).tgz -C /opt/planetwatch backend/instance backend/uploads .env` |

Download a backup to your PC with `scp -i $key "${srv}:planetwatch-backup-*.tgz" .`

The https certificate renews itself; certbot installs a timer for that.

## Other providers

`setup.sh` works on any Ubuntu 22.04/24.04 server with at least 4 GB of RAM, for example a
DigitalOcean droplet (GitHub Student Pack credit) or Hetzner. Only step 1 differs. Those
providers give you no free hostname, so use your own domain or `<ip-with-dashes>.sslip.io`
(e.g. `20-87-1-5.sslip.io`).
