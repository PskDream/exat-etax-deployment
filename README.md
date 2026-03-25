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
  │   └── deploy_docker/
  │       └── tasks/main.yml       ← logic deploy
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

### Deploy UAT
```bash
# deploy ทุก service
IMAGE_TAG=<git-sha> TARGET_SERVICES=all \
ansible-playbook deploy.yml -i inventories/uat -v

# deploy เฉพาะ service
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be \
ansible-playbook deploy.yml -i inventories/uat -v

# deploy หลาย service
IMAGE_TAG=<git-sha> TARGET_SERVICES=customer-portal-be,customer-portal-fe \
ansible-playbook deploy.yml -i inventories/uat -v
```

### Deploy PROD
```bash
IMAGE_TAG=<git-sha> TARGET_SERVICES=all \
ansible-playbook deploy.yml -i inventories/prod -v
```

### Rollback
```bash
ROLLBACK_TAG=<previous-git-sha> TARGET_SERVICES=customer-portal-be \
ansible-playbook rollback.yml -i inventories/prod -v
```

## เพิ่ม Service ใหม่
แก้แค่ `group_vars/all.yml` ของแต่ละ environment:
```yaml
services:
  my-new-service:
    app_port: 9090
    container_port: 9090
    env_file: "/opt/my-new-service/.env"
    health_path: "/health"
```
