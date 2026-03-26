# Ansible Deploy

## โครงสร้าง
```
ansible/
  ├── inventories/
  │   ├── uat/
  │   │   ├── hosts.ini            ← IP เครื่อง UAT
  │   │   └── group_vars/all.yml   ← config UAT
  │   └── prod/
  │       ├── hosts.ini            ← IP เครื่อง PROD
  │       └── group_vars/all.yml   ← config PROD
  ├── roles/
  │   ├── deploy_docker/
  │   │   ├── tasks/main.yml       ← logic deploy Docker (ECR → docker compose v2)
  │   │   └── templates/           ← docker-compose.yml.j2 ต่อ service
  │   └── deploy_systemd/
  │       └── tasks/main.yml       ← logic deploy systemd (copy JAR → restart → health)
  ├── ansible.cfg                  ← ask_pass=True, host_key_checking=False
  ├── deploy.yml
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

## การใช้งาน

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

Deployment วิ่งพร้อมกันทุก server (`serial: 0`) และหยุดทันทีถ้า host ใดล้มเหลว (`any_errors_fatal: true`)

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

## โครงสร้าง hosts.ini

```ini
[customer_portal_be_servers]
prod-server1 ansible_host=10.200.120.17
[customer_portal_be_servers:vars]
ansible_user=adminos

[rest_pdf_servers]
prod-restpdf01 ansible_host=10.200.120.61
prod-restpdf02 ansible_host=10.200.120.62
[rest_pdf_servers:vars]
ansible_user=adminos
```

ระบุ `TARGET_HOST` ตรงกับชื่อ host ใน inventory (เช่น `prod-server1`, `uat-restpdf01`)

## SSH Authentication

`ansible.cfg` ตั้งค่า `ask_pass = True` และ `become_ask_pass = True` ไว้ ทำให้ Ansible prompt ขอ SSH password และ sudo password ทุกครั้ง
