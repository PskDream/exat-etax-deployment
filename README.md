# Ansible Deploy

## โครงสร้าง
```
ansible/
  ├── inventories/
  │   ├── uat/
  │   │   ├── hosts.ini            ← IP เครื่อง UAT
  │   │   └── group_vars/all.yml   ← config UAT (ECR, services)
  │   ├── prod/
  │   │   ├── hosts.ini            ← IP เครื่อง PROD
  │   │   └── group_vars/all.yml   ← config PROD (ECR, services)
  │   └── monitoring/
  │       ├── hosts.ini            ← IP ทุก server + node_group
  │       └── group_vars/
  │           ├── all.yml          ← Prometheus/Loki/Tempo URLs
  │           ├── app_v2_servers.yml
  │           ├── rest_pdf_servers.yml
  │           ├── nginx_servers.yml
  │           ├── haproxy_servers.yml
  │           └── rest_hsm_servers.yml
  ├── roles/
  │   ├── deploy_docker/
  │   │   ├── tasks/main.yml       ← logic deploy Docker (ECR → docker compose v2)
  │   │   └── templates/           ← docker-compose.yml.j2 ต่อ service
  │   ├── deploy_systemd/
  │   │   └── tasks/main.yml       ← logic deploy systemd (copy JAR → restart → health)
  │   └── deploy_alloy/
  │       ├── tasks/
  │       │   ├── main.yml         ← เลือก path ตาม deploy_type
  │       │   ├── install_docker.yml
  │       │   └── install_systemd.yml
  │       ├── handlers/main.yml
  │       └── templates/
  │           ├── config.alloy.j2
  │           ├── docker-compose.alloy.yml.j2
  │           └── beyla.yml.j2
  ├── ansible.cfg                  ← ask_pass=True, host_key_checking=False
  ├── deploy.yml
  ├── deploy_alloy.yml
  └── rollback.yml
```

## Setup ครั้งแรก
```bash
pip install ansible --break-system-packages
ansible-galaxy collection install community.docker
```

## แก้ค่าก่อนใช้งาน
1. แก้ IP เครื่องใน `inventories/uat/hosts.ini` และ `inventories/prod/hosts.ini`
2. แก้ `ecr_registry` ใน `inventories/*/group_vars/all.yml`
3. เพิ่ม/แก้ service ใน `services:` ของแต่ละ group_vars
4. แก้ IP เครื่องใน `inventories/monitoring/hosts.ini`
5. แก้ URLs ใน `inventories/monitoring/group_vars/all.yml`

---

## การใช้งาน — App Deployment

### Test connection
```bash
ansible all -i inventories/uat -m ping
```

### Dry run
```bash
IMAGE_TAG=abc123 TARGET_HOST=uat-server1 TARGET_SERVICE=customer-portal-be \
ansible-playbook deploy.yml -i inventories/uat --check --diff
```

### Deploy Docker service (UAT)
```bash
IMAGE_TAG=<git-sha> TARGET_HOST=uat-server1 TARGET_SERVICE=customer-portal-be \
ansible-playbook deploy.yml -i inventories/uat -v
```

### Deploy Docker service (PROD)
```bash
IMAGE_TAG=<git-sha> TARGET_HOST=prod-server1 TARGET_SERVICE=customer-portal-be \
ansible-playbook deploy.yml -i inventories/prod -v
```

### Deploy Systemd service (JAR)
```bash
JAR_SRC=/path/to/rest-hsm-0.0.1-SNAPSHOT.jar \
TARGET_HOST=prod-restpdf01 TARGET_SERVICE=rest-hsm \
ansible-playbook deploy.yml -i inventories/prod -v
```

### Rollback
```bash
ROLLBACK_TAG=<previous-git-sha> TARGET_HOST=prod-server1 TARGET_SERVICE=customer-portal-be \
ansible-playbook rollback.yml -i inventories/prod -v
```

---

## การใช้งาน — Monitoring (Alloy + Beyla)

### Deploy Alloy ทุก server ใน group
```bash
TARGET_HOST=app_v2_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring -v
TARGET_HOST=nginx_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring -v
TARGET_HOST=haproxy_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring -v
TARGET_HOST=rest_pdf_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring -v
TARGET_HOST=rest_hsm_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring -v
```

### deploy_type per group

| Group | deploy_type | Beyla |
|-------|-------------|-------|
| app_v2_servers | docker | ✅ instruments app ports |
| rest_pdf_servers | docker | ✅ instruments app ports |
| nginx_servers | systemd | — |
| haproxy_servers | systemd | — |
| rest_hsm_servers | systemd | — |

- `deploy_type: docker` — ติดตั้ง Alloy + Beyla ผ่าน docker compose ใน `/opt/alloy/`
- `deploy_type: systemd` — ติดตั้ง Alloy ผ่าน apt package (grafana repo) เป็น systemd service

### เพิ่ม Beyla สำหรับ group ใหม่
แก้ `inventories/monitoring/group_vars/<group>.yml`:
```yaml
beyla_services:
  - name: my-service
    open_ports: 8080
  - name: another-service
    open_ports: 9000
```

---

## Deployment Flow

### Docker service
`deploy_docker` role ทำงานตามลำดับนี้สำหรับแต่ละ service:
1. ดึง ECR login token และ authenticate Docker
2. Pull image จาก ECR (`<ecr_registry>/<repository>:<tag>`)
3. สร้าง directory `/opt/<service_name>/` (ถ้ายังไม่มี)
4. Render `docker-compose.yml` จาก template
5. Deploy ด้วย `docker compose up` (docker_compose_v2)
6. รอ health check ผ่าน (12 retries × 5s = 60s timeout)
7. Cleanup dangling images

### Systemd service (JAR)
`deploy_systemd` role ทำงานตามลำดับนี้:
1. Copy JAR ไปยัง `jar_dest` บนเครื่อง target
2. Restart systemd service (เฉพาะถ้า JAR เปลี่ยน)
3. รอ service active (12 retries × 5s = 60s timeout)
4. รอ HTTP health check ผ่านที่ `http://localhost:<health_port><health_path>`

### Alloy (docker)
`deploy_alloy` role (docker path):
1. สร้าง `/opt/alloy/` directory
2. Render `config.alloy` และ `beyla.yml` (ถ้ามี beyla_services)
3. Pull grafana/alloy และ grafana/beyla images
4. Deploy ด้วย docker compose (recreate always)
5. รอ health check ที่ `http://localhost:12345/-/ready`

### Alloy (systemd)
`deploy_alloy` role (systemd path):
1. Add Grafana apt repository
2. Install alloy package
3. Render `config.alloy` ไปที่ `/etc/alloy/config.alloy`
4. Enable และ start alloy systemd service
5. รอ health check ที่ `http://localhost:12345/-/ready`

Deployment วิ่งพร้อมกันทุก server (`serial: 0`) และหยุดทันทีถ้า host ใดล้มเหลว (`any_errors_fatal: true`)

---

## เพิ่ม Service ใหม่

### 1. เพิ่ม service ใน group_vars
แก้ `group_vars/all.yml` ของแต่ละ environment:
```yaml
services:
  my-service:
    repository: "exat/e-tax/my-service"
    app_port: 9090
    container_port: 9090
    env_file:
      - "/opt/my-service/.env"
    health_path: "/health"
    # volumes:              ← optional
    #   - "/opt/my-service/data:/app/data"
```

### 2. เพิ่ม host ใน hosts.ini
```ini
[my_service_servers]
my-server01 ansible_host=10.200.x.x
[my_service_servers:vars]
ansible_user=adminos
```

### 3. สร้าง template (optional)
สร้าง `roles/deploy_docker/templates/docker-compose.my-service.yml.j2`
ถ้าไม่มีจะใช้ `docker-compose.yml.j2` เป็น default

### Systemd service (JAR)
```yaml
services:
  my-service:
    type: systemd
    systemd_service: my-service.service
    jar_dest: "/home/adminos/my-service/my-service.jar"
    user: root
    health_port: 8080
    health_path: "/actuator/health"
```

---

## SSH Authentication

`ansible.cfg` ตั้งค่า `ask_pass = True` และ `become_ask_pass = True` ไว้ ทำให้ Ansible prompt ขอ SSH password และ sudo password ทุกครั้ง
