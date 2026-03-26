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
IMAGE_TAG=abc123 TARGET_SERVICES=customer-portal-be ansible-playbook deploy.yml -i inventories/uat --check --diff
```

**Deploy specific service:**
```bash
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be ansible-playbook deploy.yml -i inventories/uat -v
```

**Deploy multiple services:**
```bash
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be,rest-pdf ansible-playbook deploy.yml -i inventories/uat -v
```

**Rollback:**
```bash
ROLLBACK_TAG=<previous-git-sha> TARGET_SERVICES=customer-portal-be ansible-playbook rollback.yml -i inventories/prod -v
```

## Repository Structure

- `deploy.yml` — main deployment playbook; requires `IMAGE_TAG` and `TARGET_SERVICES` env vars (comma-separated service names)
- `rollback.yml` — rollback playbook; requires `ROLLBACK_TAG` and `TARGET_SERVICES` env vars
- `inventories/uat/` and `inventories/prod/` — environment-specific host inventories and group variables
- `roles/deploy_docker/tasks/main.yml` — core deployment logic (ECR login → pull image → docker compose v2 → health check)
- `roles/deploy_systemd/tasks/main.yml` — systemd deployment logic (copy JAR → restart → health check)
- `ansible.cfg` — global Ansible config (`ask_pass=True`, `host_key_checking=False`)

## Host Group Convention

Each service maps to a dedicated host group using the naming convention `<service_name>_servers` (replacing `-` with `_`). `deploy.yml` derives the target host group automatically from `TARGET_SERVICES`:

```
TARGET_SERVICES=customer-portal-be  →  hosts: customer_portal_be_servers
TARGET_SERVICES=rest-pdf            →  hosts: rest_pdf_servers
```

All service groups are children of `service_servers` in `hosts.ini`.

## Deployment Flow

### Docker service
The `deploy_docker` role performs these steps for each service:
1. Obtain ECR login token and authenticate Docker
2. Pull image from ECR (`<ecr_registry>/<repository>:<tag>`)
3. Ensure `/opt/<service_name>/` directory exists
4. Render `docker-compose.yml` from template
5. Deploy via `docker compose up` (docker_compose_v2)
6. Wait for health check to pass (12 retries × 5s = 60s timeout)
7. Clean up dangling images

### Systemd service (JAR)
The `deploy_systemd` role performs these steps:
1. Copy JAR to `jar_dest` on target host
2. Restart systemd service (only if JAR changed)
3. Wait for service active state (12 retries × 5s = 60s timeout)
4. Wait for HTTP health check at `http://localhost:<health_port><health_path>`

Deployment is parallel across all servers (`serial: 0`) with `any_errors_fatal: true`.

## Adding a New Service

1. Add entry to `inventories/<env>/group_vars/all.yml`:

```yaml
services:
  my-new-service:
    repository: "exat/e-tax/my-new-service"
    app_port: 9090
    container_port: 9090
    env_file:
      - "/opt/my-new-service/.env"
    health_path: "/health"
```

2. Add host group to `hosts.ini` (both UAT and PROD):

```ini
[my_new_service_servers]
my-server01 ansible_host=10.200.x.x target_services=my-new-service
[my_new_service_servers:vars]
ansible_user=adminos

[service_servers:children]
...
my_new_service_servers
```

3. Optionally create `roles/deploy_docker/templates/docker-compose.my-new-service.yml.j2` (falls back to `docker-compose.yml.j2`)

## Environment Configuration

Each environment's `group_vars/all.yml` contains:
- `env` — environment name (uat/prod)
- `ecr_registry` — AWS ECR registry URL
- `aws_region` — AWS region (ap-southeast-7 for Bangkok)
- `services` — map of service definitions
