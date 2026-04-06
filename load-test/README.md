# Load Test — rest-hsm

ทดสอบ `/api/sign/pdf-hash` และ `/api/sign/xml` ด้วย Locust

## Directory structure

```
load-test/
├── locustfile.py                    # Locust script หลัก
├── prepare.py                       # สร้าง fixtures ก่อนรัน
├── ec-prime256v1-priv-key-pkcs8.pem # EC private key สำหรับ generate JWT (PKCS#8)
└── fixtures/
    ├── sample.pdf                   # PDF ต้นฉบับ (สร้างอัตโนมัติถ้าไม่มี)
    ├── sample.xml                   # XML ต้นฉบับ (สร้างอัตโนมัติถ้าไม่มี)
    ├── pdf_hash.txt                 # SHA-256 base64 ของ PDF (generated)
    └── xml.txt                      # base64-encoded XML (generated)
```

> **หมายเหตุ:** `ec-prime256v1-priv-key-pkcs8.pem` ต้องมีอยู่ในโฟลเดอร์นี้ก่อนรัน  
> ถ้าต้องการ generate key ใหม่ ดูที่ [Generate key pair](#generate-key-pair-ถ้าต้องการใหม่)

---

## Setup (ครั้งแรก)

### 1. Install dependencies

```bash
cd load-test/
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install locust PyJWT cryptography
```

### 2. สร้าง fixtures

```bash
python3 prepare.py
```

ผลลัพธ์ที่ควรเห็น:

```
[+] สร้าง fixtures/sample.pdf อัตโนมัติ (minimal PDF)
[✓] pdf_hash.txt  (688 bytes → SHA-256 base64)
[+] สร้าง fixtures/sample.xml อัตโนมัติ
[✓] xml.txt       (147 bytes → base64)

[✓] Fixtures พร้อมแล้ว รัน locust ได้เลย
```

> ถ้าต้องการใช้ PDF/XML ของตัวเองให้วางไฟล์ไว้ที่ `fixtures/sample.pdf` และ `fixtures/sample.xml` ก่อนรัน `prepare.py`

---

## Run

### Web UI (แนะนำ)

```bash
source .venv/bin/activate
locust -f locustfile.py
```

เปิด browser ไปที่ **http://localhost:8089** แล้วกำหนด:
- **Number of users** — จำนวน concurrent users
- **Spawn rate** — เพิ่ม user/วินาที
- **Host** — URL ของ app เช่น `http://10.204.61.40:9000`

### Headless (CLI / CI)

```bash
source .venv/bin/activate
locust -f locustfile.py \
  --headless \
  --host http://10.204.61.40:9000 \
  --users 20 \
  --spawn-rate 5 \
  --run-time 60s \
  --html report.html
```

| Flag | ความหมาย |
|------|----------|
| `--users` | จำนวน concurrent users สูงสุด |
| `--spawn-rate` | เพิ่ม user/วินาที (ramp-up speed) |
| `--run-time` | ระยะเวลารัน เช่น `60s`, `5m`, `1h` |
| `--html` | export รายงาน HTML |

---

## ปรับ config

แก้ค่าที่ต้นไฟล์ `locustfile.py`:

```python
BASE_URL      = "http://10.204.61.40:9000"   # URL ของ app
KEY_ALIAS     = "my-key"                      # alias ของ key ใน keystore
PRIV_KEY_PATH = "ec-prime256v1-priv-key-pkcs8.pem"
```

---

## Generate key pair (ถ้าต้องการใหม่)

```bash
# สร้าง EC key pair
openssl ecparam -name prime256v1 -genkey -noout -out ec-prime256v1-priv-key.pem
openssl ec -in ec-prime256v1-priv-key.pem -pubout -out ec-prime256v1-pub-key.pem

# แปลง private key เป็น PKCS#8
openssl pkcs8 -topk8 -nocrypt \
  -in ec-prime256v1-priv-key.pem \
  -out ec-prime256v1-priv-key-pkcs8.pem

# copy public key ไปให้ app
cp ec-prime256v1-pub-key.pem <RESOURCES_PATH>/jwt/authorizedkeys/load-test.pub
```

---

## Scenario แนะนำ

| Scenario | Users | Spawn rate | Duration | เป้าหมาย |
|----------|-------|------------|----------|----------|
| Smoke    | 1     | 1          | 30s      | ตรวจว่า endpoint ทำงานได้ |
| Load     | 20    | 5          | 3m       | วัด p95 latency ที่ normal load |
| Stress   | 100   | 10         | 5m       | หา breaking point |
| Soak     | 10    | 2          | 30m      | ตรวจ memory leak / HSM session |
