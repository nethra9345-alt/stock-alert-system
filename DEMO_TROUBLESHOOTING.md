# StockPulse AI — Demonstration Troubleshooting & Diagnostics Guide
**Stage 11: Operational Runbook for College Viva & Lab Evaluation**

---

## 1. Quick Diagnostic Checklist

Run these quick checks if anything unexpected occurs before or during your presentation:

| Check | Command | Expected Output |
| :--- | :--- | :--- |
| **Docker Daemon** | `docker info` | Displays engine version & Linux containers |
| **Containers Status** | `docker compose ps` | `stockpulse-backend (healthy)`, `stockpulse-frontend (healthy)` |
| **PostgreSQL Service** | `Get-Service -Name postgresql*` | Status: `Running` |
| **Port 80 Availability** | `netstat -ano \| findstr :80` | PID belonging to `docker-proxy.exe` |
| **Health API** | `curl.exe -s http://localhost/api/health` | `{"status":"online", "database":{"status":"connected"}}` |
| **Automated Verification** | `backend\venv\Scripts\python.exe scripts\verify_demo_deployment.py` | 11/11 Checks Passed |

---

## 2. Common Issues & Resolution

### Issue 1: "Port 80 is already allocated" or "bind: address already in use"
- **Symptom**: `docker compose up` errors stating port 80 is unavailable.
- **Cause**: Windows IIS, World Wide Web Publishing Service (W3SVC), Skype, or another web server is holding port 80.
- **Fix**:
  1. Identify the process holding port 80:
     ```powershell
     netstat -ano | findstr :80
     ```
  2. If it is IIS / W3SVC:
     ```powershell
     Stop-Service -Name W3SVC
     ```
  3. Alternatively, map a different host port in `.env`:
     ```env
     FRONTEND_PORT=8080
     ```
     and access via `http://localhost:8080`.

---

### Issue 2: Backend Container Reports "Connection refused" to PostgreSQL
- **Symptom**: `docker compose logs backend` displays:
  `psycopg.OperationalError: connection to server at "host.docker.internal", port 5432 failed: Connection refused`
- **Causes & Fixes**:
  1. **PostgreSQL service is stopped on Windows**:
     Start the service in PowerShell:
     ```powershell
     Start-Service -Name "postgresql-x64-18"
     ```
  2. **PostgreSQL is not listening on all network interfaces**:
     Open `C:\Program Files\PostgreSQL\18\data\postgresql.conf` and confirm:
     ```ini
     listen_addresses = '*'
     ```
     Restart PostgreSQL after changing:
     ```powershell
     Restart-Service -Name "postgresql-x64-18"
     ```
  3. **Client Authentication in pg_hba.conf**:
     Ensure `C:\Program Files\PostgreSQL\18\data\pg_hba.conf` permits Docker bridge subnets:
     ```text
     # IPv4 local connections from Docker containers:
     host    all             all             172.16.0.0/12            scram-sha-256
     host    all             all             192.168.0.0/16           scram-sha-256
     ```

---

### Issue 3: Login Fails with "Invalid credentials"
- **Symptom**: Login returns 401 Unauthorized for `trader_pro`.
- **Cause**: Password mismatch or altered demo account record.
- **Fix**:
  The preconfigured demo password is:
  ```
  Username: trader_pro
  Password: TraderPass@2026
  ```
  If needed, verify or reset password via the backend container:
  ```powershell
  docker compose exec backend python -c "from backend.app.core.database import SessionLocal; from backend.app.models.user import User; from backend.app.core.security import hash_password; s=SessionLocal(); u=s.query(User).filter_by(username='trader_pro').first(); u.hashed_password=hash_password('TraderPass@2026'); s.commit(); print('Password reset to TraderPass@2026 successfully'); s.close()"
  ```

---

### Issue 4: Docker Container Health Check Fails (Unhealthy status)
- **Symptom**: `docker compose ps` shows `(unhealthy)`.
- **Cause**: Inspect detailed health check failure reasons:
  ```powershell
  docker inspect --format="{{json .State.Health}}" stockpulse-backend
  docker inspect --format="{{json .State.Health}}" stockpulse-frontend
  ```
- **Fix**:
  - For `stockpulse-backend`: Verify database URL in `.env`.
  - For `stockpulse-frontend`: Verify nginx configuration with `docker compose exec frontend nginx -t`.

---

## 3. Database Safety, Backup & Disaster Recovery

### Safety Guarantees:
- **Never drop the `stockpulse` database**.
- The root directory contains the safety backup: `stockpulse_backup.dump` (112 KB).
- **Never overwrite or delete `stockpulse_backup.dump`**.

### In the Event of Accidental Data Corruption:
To restore the pre-demonstration database state from `stockpulse_backup.dump`:

1. Stop application containers:
   ```powershell
   docker compose down
   ```

2. Restore database using `pg_restore` (Windows PowerShell):
   ```powershell
   $env:PGPASSWORD = "<YOUR_POSTGRES_PASSWORD>"
   & "C:\Program Files\PostgreSQL\18\bin\pg_restore.exe" -h localhost -p 5432 -U postgres -d stockpulse --clean --if-exists stockpulse_backup.dump
   ```

3. Verify Alembic schema revision:
   ```powershell
   backend\venv\Scripts\python.exe -m alembic current
   ```
   Expected output: `d45a76e90234 (head)`

4. Restart application containers:
   ```powershell
   docker compose up -d
   ```

---

## 4. Live Container Log Streaming

To monitor logs in real-time during your presentation:

```powershell
# Follow backend API logs:
docker compose logs -f backend

# Follow frontend Nginx access & error logs:
docker compose logs -f frontend

# View last 50 lines with timestamps:
docker compose logs --tail=50 -t backend
```

---

## 5. Clean Reset / Restart Runbook

If you need a clean reboot of the demonstration containers without touching data:

```powershell
# 1. Stop containers cleanly
docker compose down

# 2. Start containers in detached mode
docker compose up -d

# 3. Wait 10 seconds and test health
curl.exe -s http://localhost/api/health
```
