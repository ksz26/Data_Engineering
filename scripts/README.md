# ДЗ №4 — скрэпинг сайта

## Что и откуда парсим

**Источник:** каталог интернет-магазина косметики «Подружка» —
https://www.podrygka.ru/catalog/

**Что парсим:** карточки товаров каталога (уход, декоративная косметика и т.д.)
с первых 20 страниц — по 20 товаров на страницу.

Скрипт [`scrap_site.py`](scrap_site.py) отправляет GET-запросы через `httpx`
(как на практике), разбирает HTML через `BeautifulSoup` и достает данные из
**JSON-LD блока** (`application/ld+json`, schema.org `Product`), который сайт
публикует у каждой карточки. Это надёжнее хрупких CSS-селекторов: разметка
каталога собрана на Tailwind и может меняться, а схема JSON-LD — нет.

| Столбец | Откуда берётся |
|---|---|
| `sku` | артикул товара (`sku`) |
| `name` | название (`name`) |
| `brand` | `brand.name` |
| `category` | путь URL карточки, например `ukhod/litso/toniki` |
| `price` | `offers.price` |
| `in_stock` | `offers.availability` заканчивается на `InStock` → булево значение |
| `rating` | `aggregateRating.ratingValue` |
| `review_count` | `aggregateRating.reviewCount` |
| `description` | описание товара (первые 200 символов) |
| `image_url` | первая ссылка из `image` |
| `url` | ссылка на карточку товара |
| `image_file` | локальный путь к скачанному фото, например `data/images/255915.webp` (заполнен у первых 10 товаров) |

Приведение типов: `price`, `review_count` → `Int64`; `rating` → дробное;
`brand`, `category` → `category`; `in_stock` → `bool`.

**Итог:** 400 строк × 12 столбцов, файл `data/podrygka_cosmetics.csv`
(в репозиторий не коммитится — папка `data/` в `.gitignore`).

## Скачивание картинок

Функция `download_images()` принимает столбец `image_url`, скачивает фото первых
`MAX_IMAGES = 10` товаров в `data/images/` (имя файла — артикул, `255915.webp`) и возвращает
столбец локальных путей с теми же индексами — он добавляется в датасет как
`image_file`. Каждое скачивание обёрнуто в `try/except`: битая ссылка не роняет
скрипт, а просто пропускается с сообщением. У остальных товаров в `image_file` пропуск.

## Запуск

Зависимости для скрэпинга (`httpx`, `beautifulsoup4`) входят в dev-блок `pyproject.toml`. Устанавливаются из корня проекта:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/scrap_site.py
```

Вывод: прогресс по страницам и по скачиванию картинок, размер датасета, типы колонок и первые 20 строк.
Запуск занимает около 20 секунд.

## Скриншоты

Выдача датасета (первые 20 строк):

![Первые 20 строк датасета](https://github.com/user-attachments/assets/cc82995d-bcd3-4d8d-847f-bae0ccd75e46)

Скачанные фото товаров (миниатюры из `data/images/`):

![Миниатюры скачанных картинок](https://github.com/user-attachments/assets/013f49fa-cd95-43c5-8680-283d9ac7fe29)

# ДЗ №7 — запись в базу данных

В ДЗ №8 эта логика встроена в пакет [`etl`](../src/etl) (`creds.py` и `load.py`), скрипты оставлены как результат ДЗ №7.

1. [`creds_to_env.py`](creds_to_env.py) читает данные для подключения из таблицы `access` в SQLite-файле и записывает их в `.env` в корне проекта.
2. [`write_to_db.py`](write_to_db.py) читает доступы из `.env` и записывает первые 100 строк `Oil_Pipeline_Accidents.csv` в таблицу `bulatovaks` базы `homeworks`. После записи скрипт проверяет количество строк. Если таблица уже существует, скрипт остановится и не перезапишет ее.

Запуск из корня проекта:

```bash
source .venv/bin/activate
python scripts/creds_to_env.py /полный/путь/к/creds.db
python scripts/write_to_db.py
```
