#!/usr/bin/env python3
"""
สร้าง fixtures ก่อนรัน locust ทุกครั้ง
  python3 prepare.py

Requires:
  - ec-prime256v1-priv-key-pkcs8.pem  (EC private key PKCS#8)
  - fixtures/sample.pdf
  - fixtures/sample.xml
"""
import base64
import hashlib
import os

PRIV_KEY_PATH = "ec-prime256v1-priv-key-pkcs8.pem"
PDF_PATH      = "fixtures/sample.pdf"
XML_PATH      = "fixtures/sample.xml"

os.makedirs("fixtures", exist_ok=True)

# --- Validate private key exists -------------------------------------------
if not os.path.exists(PRIV_KEY_PATH):
    print(f"[!] ไม่พบ {PRIV_KEY_PATH} — copy private key มาก่อน")
    raise SystemExit(1)

# --- PDF (สร้าง minimal valid PDF ถ้าไม่มีไฟล์) ----------------------------
def _make_minimal_pdf() -> bytes:
    """สร้าง minimal PDF 1.4 ที่ valid โดยไม่ต้องใช้ library ภายนอก"""
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 44 >>\nstream\n"
        b"BT /F1 12 Tf 100 750 Td (Load Test) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )
    xref_offset = len(body)
    offsets = []
    pos = 0
    for line in body.split(b"\n"):
        if line.endswith(b"obj"):
            offsets.append(pos)
        pos += len(line) + 1

    xref = (
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    )
    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return body + xref + trailer

if not os.path.exists(PDF_PATH):
    pdf_data = _make_minimal_pdf()
    with open(PDF_PATH, "wb") as f:
        f.write(pdf_data)
    print(f"[+] สร้าง {PDF_PATH} อัตโนมัติ (minimal PDF)")

with open(PDF_PATH, "rb") as f:
    pdf_bytes = f.read()
pdf_hash_b64 = base64.b64encode(hashlib.sha256(pdf_bytes).digest()).decode()
with open("fixtures/pdf_hash.txt", "w") as f:
    f.write(pdf_hash_b64)
print(f"[✓] pdf_hash.txt  ({len(pdf_bytes):,} bytes → SHA-256 base64)")

# --- XML base64 -------------------------------------------------------------
if not os.path.exists(XML_PATH):
    # สร้าง sample XML อัตโนมัติ
    sample_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document>
  <Content>Load Test Document</Content>
  <Timestamp>2026-04-03T00:00:00Z</Timestamp>
</Document>"""
    with open(XML_PATH, "wb") as f:
        f.write(sample_xml)
    print(f"[+] สร้าง {XML_PATH} อัตโนมัติ")

with open(XML_PATH, "rb") as f:
    xml_bytes = f.read()
xml_b64 = base64.b64encode(xml_bytes).decode()
with open("fixtures/xml.txt", "w") as f:
    f.write(xml_b64)
print(f"[✓] xml.txt       ({len(xml_bytes):,} bytes → base64)")

print("\n[✓] Fixtures พร้อมแล้ว รัน locust ได้เลย")
print("    locust -f locustfile.py --host http://<app-ip>:9000")
