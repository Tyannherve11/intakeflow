import io
import json
import os
import re
import time
from pathlib import Path

import boto3
import pdfplumber
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("S3_ENDPOINT", "http://localhost:8333")
BUCKET = os.getenv("S3_BUCKET", "incoming")

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"],
    region_name="us-east-1",
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)

FIELDS = {
    "claim_id": "Claim ID",
    "employee_name": "Employee Name",
    "employee_id": "Employee ID",
    "department": "Department",
    "date": "Date",
    "category": "Category",
    "amount": "Amount (USD)",
    "description": "Description",
}
REQUIRED = ["employee_name", "employee_id", "date", "amount"]


def parse_text(text: str) -> dict:
    """Transforme le texte brut d'un formulaire en dictionnaire de champs."""
    result = {}
    for key, label in FIELDS.items():
        m = re.search(rf"^{re.escape(label)}:[ \t]*(.*)$", text, re.MULTILINE)
        value = m.group(1).strip() if m else ""
        result[key] = value or None
    if result["amount"] is not None:
        try:
            result["amount"] = float(result["amount"])
        except ValueError:
            result["amount"] = None
    return result


def extract_pdf(data: bytes) -> dict:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = pdf.pages[0].extract_text() or ""
    return parse_text(text)


def list_keys() -> list:
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET):
        keys += [o["Key"] for o in page.get("Contents", [])]
    return sorted(keys)


def main() -> None:
    truth = json.loads(Path("data/samples/labels.json").read_text())
    extracted = {}
    start = time.perf_counter()
    for key in list_keys():
        body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        extracted[key] = extract_pdf(body)
    elapsed = time.perf_counter() - start

    Path("data").mkdir(exist_ok=True)
    Path("data/extracted.json").write_text(json.dumps(extracted, indent=2))

    # Comparaison avec la vérité terrain (claim_0001.pdf <-> truth[0], etc.)
    correct = {k: 0 for k in FIELDS}
    errors = []
    for idx, expected in enumerate(truth):
        name = f"claim_{idx + 1:04d}.pdf"
        got = extracted.get(name, {})
        for field in FIELDS:
            if got.get(field) == expected.get(field):
                correct[field] += 1
            else:
                errors.append((name, field, expected.get(field), got.get(field)))

    n = len(truth)
    print(f"{len(extracted)} documents traités en {elapsed:.1f} s "
          f"({elapsed / max(len(extracted), 1):.2f} s/document)")
    print("Précision par champ :")
    for field, ok in correct.items():
        print(f"  {field:<15} {ok}/{n}  ({100 * ok / n:.1f} %)")
    total_ok = sum(correct.values())
    print(f"Précision globale : {100 * total_ok / (n * len(FIELDS)):.1f} %")

    incomplete = sum(
        1 for v in extracted.values() if any(v.get(f) is None for f in REQUIRED)
    )
    print(f"Documents avec au moins un champ obligatoire manquant : {incomplete}")
    for name, field, exp, got in errors[:5]:
        print(f"  écart : {name} / {field} : attendu {exp!r}, obtenu {got!r}")


if __name__ == "__main__":
    main()
