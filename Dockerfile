# Compatibility rollback: preserve the deployed beta10 application and dependencies.
# Only the reviewed migration tree changes so readiness recognizes the expanded DB.
FROM ghcr.io/ywyz/kindergartenmanager@sha256:f4c76e24375c129e3bc0ae2b97f3a60e21f18a832e9eca49ee27d4361f9c5d34
COPY alembic/ /app/alembic/
