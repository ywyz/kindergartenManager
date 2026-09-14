# Compatibility rollback: preserve the deployed beta10 application and dependencies.
# Updated migration tree makes readiness recognize the expanded DB.
# The explicit tenant login entry also allows isolated synthetic recovery checks.
FROM ghcr.io/ywyz/kindergartenmanager@sha256:f4c76e24375c129e3bc0ae2b97f3a60e21f18a832e9eca49ee27d4361f9c5d34
COPY alembic/ /app/alembic/
COPY app/core/config.py /app/app/core/config.py
COPY app/ui/pages/login.py /app/app/ui/pages/login.py
