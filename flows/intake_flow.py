from prefect import flow, task

from src.extract import extract_all
from src.validate_load import process


@task(retries=3, retry_delay_seconds=5)
def extract_task() -> dict:
    return extract_all()


@task(retries=2, retry_delay_seconds=5)
def validate_load_task(extracted: dict) -> dict:
    return process(extracted)


@flow(name="intakeflow-claims", log_prints=True)
def run_pipeline() -> dict:
    extracted = extract_task()
    decisions = validate_load_task(extracted)

    counts = {}
    for status in decisions.values():
        counts[status] = counts.get(status, 0) + 1
    print(f"Pipeline terminé : {counts}")
    return counts


if __name__ == "__main__":
    run_pipeline()
