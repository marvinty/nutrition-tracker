# scripts/backup.sh

Daily SQLite backup + offsite sync to Proton Drive. Runs on the Proxmox LXC host
(the one running `docker compose -f docker-compose.prod.yml`), not inside a
container — it reads the DB file straight off the `macromic_data` Docker volume's
host mountpoint.

## One-time setup on the host

```bash
apt install -y sqlite3
curl https://rclone.org/install.sh | bash   # needs unzip: apt install -y unzip
rclone config   # create a remote named "proton", type protondrive
chmod +x scripts/backup.sh
```

## Cron

```bash
crontab -e
```
Add:
```
0 3 * * * /root/nutrition-tracker/scripts/backup.sh >> /var/log/macromic-backup.log 2>&1
```

Adjust the path if the repo isn't cloned to `/root/nutrition-tracker`.
