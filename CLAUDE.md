# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Ansible-based Docker deployment system for managing multi-environment (UAT/PROD) containerized applications on AWS ECR. Deploys services via SSH to target app servers.

## Prerequisites

```bash
pip install ansible --break-system-packages
ansible-galaxy collection install community.docker
```

## Common Commands

**Test connectivity:**
```bash
ansible app_servers -i inventories/uat -m ping
```

**Dry run (check mode):**
```bash
IMAGE_TAG=abc123 ansible-playbook deploy.yml -i inventories/uat --check --diff
```

**Deploy all services:**
```bash
IMAGE_TAG=<git-sha> TARGET_SERVICES=all ansible-playbook deploy.yml -i inventories/uat -v
```

**Deploy specific service:**
```bash
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be ansible-playbook deploy.yml -i inventories/uat -v
```

**Rollback:**
```bash
ROLLBACK_TAG=<previous-git-sha> TARGET_SERVICES=customer-portal-be ansible-playbook rollback.yml -i inventories/prod -v
```

## Repository Structure

- `deploy.yml` — main deployment playbook; requires `IMAGE_TAG` env var; accepts optional `TARGET_SERVICES` (comma-separated or `all`)
- `rollback.yml` — rollback playbook; requires `ROLLBACK_TAG` env var; accepts optional `TARGET_SERVICES`
- `inventories/uat/` and `inventories/prod/` — environment-specific host inventories and group variables
- `roles/deploy_docker/tasks/main.yml` — core deployment logic (ECR login → pull image → replace container → health check)

## Deployment Flow

The `deploy_docker` role performs these steps for each service:
1. Obtain ECR login token and authenticate Docker
2. Pull image from ECR (`<ecr_registry>/<service>:<tag>`)
3. Stop and remove the existing container
4. Start new container with restart policy, health check, port mapping, and env file
5. Wait for health check to pass (12 retries × 5s = 60s timeout)
6. Clean up dangling images

Deployment is parallel across all servers (`serial: 0`) with `any_errors_fatal: true`.

## Adding a New Service

Add an entry to `inventories/<env>/group_vars/all.yml`:

```yaml
services:
  my-new-service:
    app_port: 9090
    container_port: 9090
    env_file: "/opt/my-new-service/.env"
    health_path: "/health"
```

## Environment Configuration

Each environment's `group_vars/all.yml` contains:
- `env` — environment name (uat/prod)
- `ecr_registry` — AWS ECR registry URL
- `aws_region` — AWS region (ap-southeast-7 for Bangkok)
- `services` — map of service definitions

SSH authentication uses key-based auth for UAT (`/opt/teamcity/deploy_key`) and password-based for prod (configured in `hosts.ini`).
