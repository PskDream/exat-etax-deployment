# Deployments

[//]: # (IMAGE_TAG=06d2944 TARGET_HOST=app_v2_servers TARGET_SERVICE=generator \)
[//]: # (ansible-playbook deploy.yml -i inventories/uat -v)
## generator
9fd695d
33f6ce9
1486793
8312f60
8f555ba
IMAGE_TAG=v1.5.0 TARGET_HOST=app_v2_servers TARGET_SERVICE=generator \
ansible-playbook deploy.yml -i inventories/uat -v

8f980c0
33f6ce9
1486793
IMAGE_TAG=8312f60 TARGET_HOST=app_v2_servers TARGET_SERVICE=generator SERIAL=1 \
ansible-playbook deploy.yml -i inventories/prod -v

## staff-portal
IMAGE_TAG=v1.1.0 TARGET_HOST=staff_servers TARGET_SERVICE=staff-portal \
ansible-playbook deploy.yml -i inventories/uat -v
IMAGE_TAG=v1.1.0 TARGET_HOST=staff_servers TARGET_SERVICE=staff-portal-be \
ansible-playbook deploy.yml -i inventories/uat -v

## send-xml-to-h2h
IMAGE_TAG=v1.0.0 TARGET_HOST=sent_xml_servers TARGET_SERVICE=send-xml-to-h2h \
ansible-playbook deploy.yml -i inventories/uat -v

## customer-portal-be
9525d3b
IMAGE_TAG=7fd8831 TARGET_HOST=app_v2_servers TARGET_SERVICE=customer-portal-be \
ansible-playbook deploy.yml -i inventories/uat -v
9525d3b
IMAGE_TAG=7fd8831 TARGET_HOST=customer_servers TARGET_SERVICE=customer-portal-be SERIAL=1 \
ansible-playbook deploy.yml -i inventories/prod -v
# Monitoring
TARGET_HOST=rest_hsm_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring-prod -v
TARGET_HOST=app_v2_servers ansible-playbook deploy_alloy.yml -i inventories/monitoring-prod -v
