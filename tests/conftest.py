import os

# Valeurs factices : les tests ne se connectent à rien, mais les modules
# lisent ces variables à l'import.
for name in ["S3_ACCESS_KEY", "S3_SECRET_KEY", "POSTGRES_DB",
             "POSTGRES_USER", "POSTGRES_PASSWORD"]:
    os.environ.setdefault(name, "test")
