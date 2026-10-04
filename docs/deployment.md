# Deployment

## Local
1. Copy .env.example to .env.
2. Start the Docker Compose stack.
3. Initialize the schema with python -m packages.db.bootstrap.
4. Run the API at port 8000.

## Production
Use docker-compose.prod.yml behind TLS. Set strong database credentials, restrict Redis/Postgres network exposure, store secrets in a deployment secret manager, and schedule PostgreSQL backups.

This is a production baseline, not a cloud-specific deployment. Restore testing, managed secret rotation, image signing, vulnerability scanning, and TLS automation should be completed before sensitive workloads.