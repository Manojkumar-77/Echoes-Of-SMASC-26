# P-GALLERY — BACKUP & DISASTER RECOVERY PROTOCOL

---

## 1. BACKUP STRATEGY OVERVIEW

P-Gallery separates state into two distinct subsystems:
1. **Relational Database (PostgreSQL / SQLite)**: Stores user accounts, CMS text content, timeline events, categories, and media references.
2. **Binary Media Storage (Local Volume / S3-Compatible Object Storage)**: Stores image and video files.

Both must be backed up independently to ensure complete recovery.

---

## 2. DATABASE BACKUP & RESTORE

### A. PostgreSQL (Production Docker / Cloud)

#### Automated Backup Command
```bash
# Generate compressed SQL dump with timestamp
docker compose exec db pg_dump -U postgres -d pgallery -F c -b -v -f /var/lib/postgresql/data/backup_$(date +%Y%m%d_%H%M%S).dump
```

#### Copy Dump from Container to Host / Backup Storage
```bash
docker compose cp db:/var/lib/postgresql/data/backup_latest.dump ./backups/
```

#### Restoration Procedure
```bash
# 1. Stop web container to prevent incoming writes
docker compose stop web

# 2. Restore dump into PostgreSQL
docker compose exec -T db pg_restore -U postgres -d pgallery --clean --no-owner /var/lib/postgresql/data/backup_latest.dump

# 3. Restart web container
docker compose start web
```

### B. SQLite (Development & Local Fallback)
```bash
# Create consistent SQLite snapshot
sqlite3 db.sqlite3 ".backup 'backups/db_backup_$(date +%Y%m%d_%H%M%S).sqlite3'"
```

---

## 3. MEDIA STORAGE BACKUP & RESTORE

### A. Local Persistent Volume (`USE_S3=False`)

#### Backup Command
```bash
# Tar and compress the media volume
tar -czvf backups/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz ./media/
```

#### Restore Command
```bash
tar -xzvf backups/media_backup_latest.tar.gz -C ./
```

### B. S3-Compatible Object Storage (`USE_S3=True` — Cloudflare R2 / AWS S3 / MinIO)

#### S3 Sync / Replication
```bash
# Sync S3 bucket to a secondary disaster-recovery bucket or local backup directory
aws s3 sync s3://pgallery-media s3://pgallery-media-backup --endpoint-url https://<account_id>.r2.cloudflarestorage.com
```

*Enable Bucket Versioning in your cloud provider console to protect against accidental deletion or corruption.*

---

## 4. DISASTER RECOVERY TIMELINE & RECOVERY POINT OBJECTIVE (RPO)

| Subsystem | Backup Frequency | Target RPO | Target RTO |
| :--- | :--- | :---: | :---: |
| **PostgreSQL Database** | Daily automated cron snapshot | $\le 24\text{ hours}$ | $< 15\text{ minutes}$ |
| **Media Storage** | Daily rsync / S3 bucket replication | $\le 24\text{ hours}$ | $< 30\text{ minutes}$ |
| **Configuration (`.env`)** | Secure vault backup upon change | $0\text{ hours}$ | $< 5\text{ minutes}$ |

