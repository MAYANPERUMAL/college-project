# Enable full compatibility for MySQL 8.0.x on Windows
try:
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.minimum_database_version = (8, 0, 0)
except Exception:
    pass
