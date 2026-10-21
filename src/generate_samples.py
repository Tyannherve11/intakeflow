import json
import random
import shutil
from datetime import date
from pathlib import Path

from faker import Faker
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Bandit B311 is ignored on the lines below: this script only generates
# synthetic test data, seeded for reproducibility. Nothing here is security-related.
fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

OUT = Path("data/samples")
OUT.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["Travel", "Meals", "Lodging", "Supplies", "Training"]
DEPARTMENTS = ["Finance", "IT", "HR", "Operations"]
REQUIRED = ["employee_name", "employee_id", "date", "amount"]


def make_claim(i: int) -> dict:
    return {
        "claim_id": f"RC-2026-{i:04d}",
        "employee_name": fake.name(),
        "employee_id": f"E{fake.random_int(10000, 99999)}",
        "department": random.choice(DEPARTMENTS),  # nosec B311
        "date": fake.date_between_dates(date(2026, 7, 1), date(2026, 9, 30)).isoformat(),
        "category": random.choice(CATEGORIES),  # nosec B311
        "amount": round(random.uniform(15, 1800), 2),  # nosec B311
        "description": fake.sentence(nb_words=8),
    }


def write_pdf(claim: dict, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "EXPENSE REIMBURSEMENT REQUEST")
    c.setFont("Helvetica", 12)
    y = 680
    labels = [
        ("Claim ID", "claim_id"), ("Employee Name", "employee_name"),
        ("Employee ID", "employee_id"), ("Department", "department"),
        ("Date", "date"), ("Category", "category"),
        ("Amount (USD)", "amount"), ("Description", "description"),
    ]
    for label, key in labels:
        value = claim.get(key)
        c.drawString(72, y, f"{label}: {'' if value is None else value}")
        y -= 28
    c.save()


def main(n: int = 100) -> None:
    truth = []
    for i in range(1, n + 1):
        claim = make_claim(i)
        # ~10 % de dossiers volontairement incomplets
        if random.random() < 0.10:  # nosec B311
            claim[random.choice(REQUIRED)] = None  # nosec B311
        write_pdf(claim, OUT / f"claim_{i:04d}.pdf")
        truth.append(claim)

    # 5 doublons exacts (même contenu, autre nom de fichier)
    for k, src in enumerate(random.sample(range(1, n + 1), 5), start=1):  # nosec B311
        dup = OUT / f"claim_{n + k:04d}.pdf"
        shutil.copy(OUT / f"claim_{src:04d}.pdf", dup)
        truth.append({**truth[src - 1], "_duplicate_of": src})

    (OUT / "labels.json").write_text(json.dumps(truth, indent=2))
    print(f"{n} PDF + 5 doublons générés dans {OUT}")


if __name__ == "__main__":
    main()
