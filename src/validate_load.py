import json
import os
from datetime import date
from pathlib import Path
from typing import LiteralString, cast

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()

REQUIRED = ["employee_name", "employee_id", "date", "amount"]


def connect():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def validate(rec: dict):
    """Retourne (statut, liste_de_problèmes, date_parsée)."""
    issues = []
    for field in REQUIRED:
        if rec.get(field) is None:
            issues.append(f"missing_field:{field}")

    claim_date = None
    if rec.get("date"):
        try:
            claim_date = date.fromisoformat(rec["date"])
            if claim_date > date.today():
                issues.append("future_date")
        except ValueError:
            issues.append("invalid_date")

    amount = rec.get("amount")
    if amount is not None and amount <= 0:
        issues.append("invalid_amount")

    return ("rejected" if issues else "valid"), issues, claim_date


def expected_status(truth: dict) -> str:
    if any(truth.get(f) is None for f in REQUIRED):
        return "rejected"
    if "_duplicate_of" in truth:
        return "duplicate"
    return "valid"


def process(extracted: dict) -> dict:
    """Valide, détecte les doublons, écrit en base. Retourne {fichier: statut}."""
    seen = {}
    decisions = {}

    # schema.sql est un fichier du projet (de confiance) : cast pour le vérificateur de types
    schema_sql = cast(
        LiteralString, Path("src/schema.sql").read_text(encoding="utf-8-sig")
    )

    with connect() as conn:
        conn.execute(schema_sql)

        for source_key in sorted(extracted):
            rec = extracted[source_key]
            status, issues, claim_date = validate(rec)

            if status == "valid":
                key = (rec["employee_id"], rec["date"], rec["amount"], rec["category"])
                if key in seen:
                    status = "duplicate"
                    issues = [f"duplicate_of:{seen[key]}"]
                else:
                    seen[key] = source_key

            decisions[source_key] = status

            conn.execute(
                """
                INSERT INTO claims (source_key, claim_id, employee_name, employee_id,
                                    department, claim_date, category, amount,
                                    description, status, issues)
                VALUES (%(source_key)s, %(claim_id)s, %(employee_name)s, %(employee_id)s,
                        %(department)s, %(claim_date)s, %(category)s, %(amount)s,
                        %(description)s, %(status)s, %(issues)s)
                ON CONFLICT (source_key) DO UPDATE SET
                    claim_id = EXCLUDED.claim_id,
                    employee_name = EXCLUDED.employee_name,
                    employee_id = EXCLUDED.employee_id,
                    department = EXCLUDED.department,
                    claim_date = EXCLUDED.claim_date,
                    category = EXCLUDED.category,
                    amount = EXCLUDED.amount,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    issues = EXCLUDED.issues,
                    processed_at = now()
                """,
                {
                    "source_key": source_key,
                    "claim_id": rec.get("claim_id"),
                    "employee_name": rec.get("employee_name"),
                    "employee_id": rec.get("employee_id"),
                    "department": rec.get("department"),
                    "claim_date": claim_date,
                    "category": rec.get("category"),
                    "amount": rec.get("amount"),
                    "description": rec.get("description"),
                    "status": status,
                    "issues": Jsonb(issues),
                },
            )
            conn.execute(
                "INSERT INTO audit_log (source_key, event, detail) VALUES (%s, %s, %s)",
                (source_key, f"validated:{status}", Jsonb({"issues": issues})),
            )

    return decisions


def main() -> None:
    extracted = json.loads(Path("data/extracted.json").read_text(encoding="utf-8"))
    truth = json.loads(Path("data/samples/labels.json").read_text(encoding="utf-8"))

    decisions = process(extracted)

    with connect() as conn:
        counts = conn.execute(
            "SELECT status, COUNT(*) FROM claims GROUP BY status ORDER BY status"
        ).fetchall()

    print("Résultat en base :")
    for status, n in counts:
        print(f"  {status:<10} {n}")

    correct = 0
    for idx, t in enumerate(truth):
        name = f"claim_{idx + 1:04d}.pdf"
        if decisions.get(name) == expected_status(t):
            correct += 1
        else:
            print(f"  écart : {name} -> {decisions.get(name)} (attendu {expected_status(t)})")
    print(f"Décisions conformes à la vérité terrain : {correct}/{len(truth)}")


if __name__ == "__main__":
    main()