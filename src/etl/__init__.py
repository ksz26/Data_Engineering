"""ETL датасета Oil Pipeline Accidents (PHMSA, 2010–2017).

Модули:
    extract   — скачивание сырого CSV с Google Drive и чтение
    transform — типы, чистка, флаги качества, имена столбцов в snake_case
    validate  — схемы Pandera для сырых и обработанных данных
    load      — Parquet и запись до 100 строк в PostgreSQL
    creds     — доступы к базе: SQLite-файл -> .env -> подключение
    errors    — EtlError и его подклассы для каждого шага
    main      — CLI, запускает весь цикл
"""

__version__ = "1.0.0"
