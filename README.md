# Ansible Deploy

## โครงสร้าง
```
ansible/
  ├── inventories/
  │   ├── uat/
  │   │   ├── hosts.ini            ← IP เครื่อง UAT + target_services ต่อ host
  │   │   └── group_vars/all.yml   ← config UAT
  │   └── prod/
  │       ├── hosts.ini            ← IP เครื่อง PROD + target_services ต่อ host
  │       └── group_vars/all.yml   ← config PROD
  ├── roles/
  │   ├── deploy_docker/
  │   │   ├── tasks/main.yml       ← logic deploy Docker (ECR → docker compose)
  │   │   └── templates/           ← docker-compose.yml.j2 ต่อ service
  │   └── deploy_systemd/
  │       └── tasks/main.yml       ← logic deploy systemd (copy JAR → restart)
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
ansible app_servers -i inventories/uat -m ping
```

### Dry run
```bash
IMAGE_TAG=abc123 ansible-playbook deploy.yml -i inventories/uat --check --diff
```

### Deploy Docker service (UAT)
```bash
# deploy ทุก service
IMAGE_TAG=<git-sha> TARGET_SERVICES=all \
ansible-playbook deploy.yml -i inventories/uat -v

# deploy เฉพาะ service
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be \
ansible-playbook deploy.yml -i inventories/uat -v

# deploy หลาย service
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be,rest-pdf \
ansible-playbook deploy.yml -i inventories/uat -v
```

### Deploy Docker service (PROD)
```bash
IMAGE_TAG=<git-sha> TARGET_SERVICES=all \
ansible-playbook deploy.yml -i inventories/prod -v
```

### Deploy Systemd service (JAR)
```bash
JAR_SRC=/path/to/rest-hsm-0.0.1-SNAPSHOT.jar \
TARGET_SERVICES=rest-hsm \
ansible-playbook deploy.yml -i inventories/prod -v
```

### Rollback
```bash
ROLLBACK_TAG=<previous-git-sha> TARGET_SERVICES=customer-portal-be \
ansible-playbook rollback.yml -i inventories/prod -v
```

## เพิ่ม Service ใหม่

### Docker service
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

สร้าง template แยกได้ที่ `roles/deploy_docker/templates/docker-compose.my-service.yml.j2`
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

## กำหนด Service ต่อ Host
ระบุ `target_services` ใน `hosts.ini` ได้ต่อ host:
```ini
prod-app01 ansible_host=10.200.120.11 target_services=customer-portal-be
prod-app02 ansible_host=10.200.120.12 target_services=customer-portal-be,rest-pdf
```
ถ้า run พร้อม `TARGET_SERVICES=xxx` จาก CLI จะ override ค่าใน hosts.ini ทุก host
