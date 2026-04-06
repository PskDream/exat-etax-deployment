import time
import uuid

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from locust import HttpUser, task, between

# ---- Config ---------------------------------------------------------------
BASE_URL      = "http://10.200.120.130:9000"
PRIV_KEY_PATH = "ec-prime256v1-priv-key-pkcs8.pem"

# Load EC private key once at module level
with open(PRIV_KEY_PATH, "rb") as f:
    _ec_private_key = load_pem_private_key(f.read(), password=None)

# ---------------------------------------------------------------------------

def _make_jwt() -> str:
    now = int(time.time())
    return jwt.encode(
        {"iat": now, "exp": now + 300, "sub": "load-test"},
        _ec_private_key,
        algorithm="ES256",
        headers={"alg": "ES256", "typ": "JWT", "kid": "service-a-2026"},
    )

def _invoice_body(doc_id: str) -> dict:
    """สร้าง request body โดย inject doc_id ที่ unique per request"""
    return {
        "exchangedDocument": {
            "id": doc_id,
            "typeCode": "T01",
            "issueDateTime": "2026-02-23T10:51:21",
        },
        "supplyChainTradeTransaction": {
            "applicableHeaderTradeAgreement": {
                "sellerTradeParty": {
                    "id": ["0010"]
                },
                "buyerTradeParty": {
                    "id": ["B2499134454"],
                    "name": "น.ส.ณัฐริกา นาคะไพฑูรย์",
                    "specifiedTaxRegistration": {
                        "id": {"schemeID": "NIDN", "value": "1659900834634"}
                    },
                    "postalTradeAddress": {
                        "postcodeCode": "10310",
                        "lineOne": "Life Asoke 46/1209 ชั้น 27 ถนน ดินแดงบางกะปิ เขตห้วยขวาง กรุงเทพมหานคร",
                        "countryID": "TH",
                    },
                },
                "additionalReferencedDocument": [],
            },
            "applicableHeaderTradeSettlement": {
                "invoiceCurrencyCode": "THB",
                "applicableTradeTaxes": [
                    {
                        "typeCode": "FRE",
                        "calculatedRate": "0",
                        "basisAmount": [{"currencyID": "THB", "value": "40257"}],
                        "calculatedAmount": [{"currencyID": "THB", "value": "0.00"}],
                    }
                ],
                "specifiedTradeAllowanceCharge": [
                    {
                        "chargeIndicator": False,
                        "actualAmount": [{"currencyID": "THB", "value": "0.00"}],
                    }
                ],
                "specifiedTradeSettlementHeaderMonetarySummation": {
                    "lineTotalAmount":    [{"currencyID": "THB", "value": "40257.00"}],
                    "allowanceTotalAmount":[{"currencyID": "THB", "value": "0.00"}],
                    "chargeTotalAmount":  [{"currencyID": "THB", "value": "0.00"}],
                    "taxBasisTotalAmount":[{"currencyID": "THB", "value": "40257.00"}],
                    "taxTotalAmount":     [{"currencyID": "THB", "value": "0.00"}],
                    "grandTotalAmount":   [{"currencyID": "THB", "value": "40257.00"}],
                },
            },
            "includedSupplyChainTradeLineItem": [
                {
                    "associatedDocumentLineDocument": {"lineID": "1"},
                    "specifiedTradeProduct": {
                        "name": [{"languageID": "TH", "value": "ค่าเช่า ปีที่ 1 เดือนที่ 1"}],
                        "informationNote": [
                            {"subject": "TransactionReference", "content": ["4100010678"]}
                        ],
                        "originTradeCountry": {"id": "TH"},
                    },
                    "specifiedLineTradeAgreement": {
                        "grossPriceProductTradePrice": {
                            "chargeAmount": [{"currencyID": "THB", "value": "13419.00"}],
                            "appliedTradeAllowanceCharge": [{"chargeIndicator": False}],
                        }
                    },
                    "specifiedLineTradeDelivery": {
                        "billedQuantity": {"unitCode": "EA", "value": "3"}
                    },
                    "specifiedLineTradeSettlement": {
                        "applicableTradeTax": [
                            {
                                "typeCode": "FRE",
                                "calculatedRate": "0",
                                "basisAmount": [{"currencyID": "THB", "value": "13419.00"}],
                                "calculatedAmount": [{"currencyID": "THB", "value": "0.00"}],
                            }
                        ],
                        "specifiedTradeAllowanceCharge": [{"chargeIndicator": False}],
                        "specifiedTradeSettlementLineMonetarySummation": {
                            "taxTotalAmount":                [{"currencyID": "THB", "value": "0.00"}],
                            "netLineTotalAmount":            [{"currencyID": "THB", "value": "40257.00"}],
                            "netIncludingTaxesLineTotalAmount": [{"currencyID": "THB", "value": "40257.00"}],
                        },
                    },
                }
            ],
        },
        "sellerBranchCode":   "00000",
        "customerBranchCode": "",
        "smartCardNumber":    "",
        "contractNumber":     "REQ6606000181",
        "carRegistration":    "",
        "carProvince":        "",
        "dealDate":           "",
        "dealDateText":       "ชำระภายในวันที่ - ค่าปรับ - บาท/วัน",
        "rentalDescription":  "",
        "paymentChanel":      "10",
        "mid":                "",
        "tid":                "",
        "approvalCode":       "",
        "bankCheque":         "ธนาคารกรุงเทพ",
        "chequeNumber":       "11111",
        "chequeDate":         "2023-07-12T00:00:00.000Z",
        "fastService":        "",
        "remark":             "",
        "formNumber":         "",
        "fiDoc":              "",
        "advice":             "",
        "requestSendMail":    "N",
        "channel":            "LRS",
        "topic":              "LRS001",
        "serviceType":        "001",
        "obu":                "",
        "customerAccountID":  "",
        "postingDate":        "2024-08-29T10:51:21",
        "postBy":             "SYSTEM",
        "txnExitDate":        "",
        "csDate":             "",
        "email":              "",
        "contractTerm":       "",
        "reference1":         "",
        "reference2":         "",
        "billPaymentFlag":    "Y",
        "advice002":          "",
        "fiscalYear":         "",
        "plazaID":            "",
        "fiscalYearRef":      "",
    }


class InvoiceUser(HttpUser):
    host = BASE_URL
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self._token_exp = 0
        self._refresh_token()

    def _refresh_token(self):
        self.headers = {
            "Authorization": f"Bearer {_make_jwt()}",
            "Content-Type": "application/json",
        }
        self._token_exp = int(time.time()) + 240

    def _ensure_token(self):
        if time.time() >= self._token_exp:
            self._refresh_token()

    @task
    def create_document(self):
        self._ensure_token()
        # ใช้ short UUID เป็น suffix เพื่อให้ doc_id ไม่ซ้ำกันแต่ละ request
        doc_id = f"LOAD_{uuid.uuid4().hex[:12].upper()}"
        self.client.post(
            "/api/v2/invoice/create-document",
            json=_invoice_body(doc_id),
            headers=self.headers,
            name="/api/v2/invoice/create-document",
        )
