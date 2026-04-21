# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Ansible-based deployment system for managing multi-environment (UAT/PROD) containerized applications on AWS ECR, and monitoring agents (Grafana Alloy + Beyla) across all servers.

## Prerequisites

```bash
pip install ansible --break-system-packages
ansible-galaxy collection install community.docker
```

## Common Commands

**Test connectivity:**
```bash
ansible all -i inventories/uat -m ping
ansible all -i inventories/monitoring -m ping
```

**Dry run (check mode):**
```bash
IMAGE_TAG=abc123 TARGET_HOST=uat-server1 TARGET_SERVICE=customer-portal-be ansible-playbook deploy.yml -i inventories/uat --check --diff
```

**Deploy a service:**
```bash
IMAGE_TAG=<git-sha> TARGET_HOST=uat-server1 TARGET_SERVICE=customer-portal-be ansible-playbook deploy.yml -i inventories/uat -v
```

**Deploy monitoring (Alloy + Beyla) — UAT:**
```bash
TARGET_HOST=app_v2_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring -v
```

**Deploy monitoring (Alloy + Beyla) — PROD:**
```bash
TARGET_HOST=app_v2_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring-prod -v
```

**Rollback:**
```bash
ROLLBACK_TAG=<previous-git-sha> TARGET_HOST=prod-server1 TARGET_SERVICE=customer-portal-be ansible-playbook rollback.yml -i inventories/prod -v
```

## Repository Structure

- `deploy.yml` — main deployment playbook; requires `IMAGE_TAG`, `TARGET_HOST`, and `TARGET_SERVICE` env vars
- `deploy_alloy.yml` — monitoring deployment playbook; requires `TARGET_HOST` env var
- `rollback.yml` — rollback playbook; requires `ROLLBACK_TAG`, `TARGET_HOST`, and `TARGET_SERVICE` env vars
- `inventories/uat/` and `inventories/prod/` — environment-specific host inventories and group variables for app deployments
- `inventories/monitoring/` — inventory for Alloy/Beyla monitoring deployment across UAT servers
- `inventories/monitoring-prod/` — inventory for Alloy/Beyla monitoring deployment across PROD servers
- `roles/deploy_docker/tasks/main.yml` — core deployment logic (ECR login → pull image → docker compose v2 → health check)
- `roles/deploy_systemd/tasks/main.yml` — systemd deployment logic (copy JAR → restart → health check)
- `roles/deploy_alloy/tasks/main.yml` — monitoring agent deployment; routes to install_docker.yml or install_systemd.yml based on `deploy_type`
- `roles/deploy_alloy/templates/` — config.alloy.j2, docker-compose.alloy.yml.j2, beyla.yml.j2
- `ansible.cfg` — global Ansible config (`ask_pass=True`, `become_ask_pass=True`, `host_key_checking=False`)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TARGET_HOST` | yes | hostname or group name from inventory (e.g. `uat-server1`, `app_v2_servers`) |
| `TARGET_SERVICE` | deploy.yml only | service name as defined in `group_vars/all.yml` |
| `IMAGE_TAG` | Docker only | ECR image tag / git SHA |
| `JAR_SRC` | systemd only | local path to JAR file |
| `ROLLBACK_TAG` | rollback only | previous image tag to roll back to |

## Deployment Flow

### Docker service
The `deploy_docker` role performs these steps:
1. Obtain ECR login token and authenticate Docker
2. Pull image from ECR (`<ecr_registry>/<repository>:<tag>`)
3. Ensure `/opt/<service_name>/` directory exists (with `become: true`)
4. Render `docker-compose.yml` from template (with `become: true`)
5. Deploy via `docker compose up` (docker_compose_v2)
6. Wait for health check to pass (12 retries × 5s = 60s timeout)
7. Clean up dangling images

### Systemd service (JAR)
The `deploy_systemd` role performs these steps:
1. Copy JAR to `jar_dest` on target host
2. Restart systemd service (only if JAR changed)
3. Wait for service active state (12 retries × 5s = 60s timeout)
4. Wait for HTTP health check at `http://localhost:<health_port><health_path>`

### Alloy + Beyla (monitoring)
The `deploy_alloy` role routes based on `deploy_type` (default: `docker`):

**docker path** (`app_v2_servers`, `rest_pdf_servers`):
1. Create `/opt/alloy/` owned by adminos
2. Render `config.alloy`, `docker-compose.yml`, and `beyla.yml` (if `beyla_services` defined)
3. Pull grafana/alloy and grafana/beyla images
4. Deploy via docker compose (`recreate: always`)
5. Wait for `http://localhost:12345/-/ready`

**systemd path** (`nginx_servers`, `haproxy_servers`, `rest_hsm_servers`):
1. Add Grafana apt repository and install alloy package
2. Render `config.alloy` to `/etc/alloy/config.alloy`
3. Enable and start alloy systemd service
4. Wait for `http://localhost:12345/-/ready`

Deployment is parallel across all servers (`serial: 0`) with `any_errors_fatal: true`.

## Monitoring Inventory Structure

Two inventories mirror the same group structure:
- `inventories/monitoring/` — UAT (`env: uat`)
- `inventories/monitoring-prod/` — PROD (`env: prod`)

`group_vars/all.yml` — shared URLs per environment:
- `env` — environment label attached to all metrics/logs/traces (`uat` or `prod`)
- `alloy_prometheus_url` — Prometheus remote write endpoint
- `alloy_loki_url` — Loki push endpoint
- `alloy_tempo_url` — Tempo OTLP HTTP endpoint

Per-group variables:
- `node_group` — label attached to all metrics/logs (set in `hosts.ini` `[group:vars]`)
- `deploy_type` — `docker` (default) or `systemd`
- `beyla_services` — list of `{name, open_ports}` to instrument with Beyla (docker groups only)

### Beyla resource attributes
`config.alloy.j2` injects `environment` and `nodename` as OTLP resource attributes on all Beyla metrics and traces via `otelcol.processor.transform "beyla"` before forwarding to Prometheus and Tempo.

### Beyla process exclusions
`beyla.yml.j2` excludes `dockerd`, `containerd`, and `docker-proxy` from instrumentation via `discovery.exclude.exe_path`. Add additional process names as `|`-separated regex patterns.

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

2. Add host to `hosts.ini` (both UAT and PROD):

```ini
[my_new_service_servers]
my-server01 ansible_host=10.200.x.x
[my_new_service_servers:vars]
ansible_user=adminos
```

3. Optionally create `roles/deploy_docker/templates/docker-compose.my-new-service.yml.j2` (falls back to `docker-compose.yml.j2`)

## Adding a New Server to Monitoring

1. Add to `inventories/monitoring/hosts.ini` (UAT) and/or `inventories/monitoring-prod/hosts.ini` (PROD):
```ini
[my_servers]
my-server01 ansible_host=10.200.x.x
[my_servers:vars]
ansible_user=adminos
node_group=MY-GROUP
```

2. Create `inventories/monitoring/group_vars/my_servers.yml` (and monitoring-prod equivalent):
```yaml
# For servers without Docker:
deploy_type: systemd

# For servers with Docker + Beyla:
beyla_services:
  - name: my-service
    open_ports: 8080
```

## Environment Configuration

Each environment's `group_vars/all.yml` contains:
- `env` — environment name (uat/prod)
- `ecr_registry` — AWS ECR registry URL
- `aws_region` — AWS region (ap-southeast-7 for Bangkok)
- `services` — map of service definitions
