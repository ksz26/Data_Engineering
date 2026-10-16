import json
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
import pandas as pd
from bs4 import BeautifulSoup


URL = "https://www.podrygka.ru"
CATALOG_PATH = "/catalog/"

MAX_PAGES = 20
DELAY = 0.5
MAX_IMAGES = 10
IMG_DELAY = 0.2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUT_FILE = DATA_DIR / "podrygka_cosmetics.csv"
IMAGES_DIR = DATA_DIR / "images"

def get_products(html: str) -> list[dict]:
    """Достаёт список товаров из JSON-LD блока (schema.org Product)."""
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", {"type": "application/ld+json"})
    if script is None or not script.string:
        return []

    data = json.loads(script.string)
    entity = data.get("mainEntity")

    if isinstance(entity, list):
        entity = next(
            (e for e in entity if isinstance(e, dict) and "itemListElement" in e),
            None,
        )
    if not isinstance(entity, dict):
        return []

    return [el.get("item", {}) for el in entity.get("itemListElement", [])]


def extract_row(product: dict) -> Optional[dict]:
    name = product.get("name")
    if not name:
        return None

    offers = product.get("offers") or {}
    rating = product.get("aggregateRating") or {}

    path = urlparse(product.get("url", "")).path.strip("/").split("/")
    category = "/".join(path[1:-1]) if len(path) > 2 else ""

    availability = str(offers.get("availability", ""))
    description = str(product.get("description", "")).replace("\n", " ").strip()
    images = product.get("image") or []

    return {
        "sku": product.get("sku"),
        "name": name,
        "brand": (product.get("brand") or {}).get("name"),
        "category": category,
        "price": offers.get("price"),
        "in_stock": availability.endswith("InStock"),
        "rating": rating.get("ratingValue"),
        "review_count": rating.get("reviewCount"),
        "description": description[:200],
        "image_url": images[0] if images else None,
        "url": product.get("url"),
    }

def download_images(image_urls: pd.Series, names: pd.Series) -> pd.Series:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    image_urls = image_urls.head(MAX_IMAGES)

    image_files = []
    indexes = []

    with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        for i, image_url in image_urls.items():
            if not image_url:
                continue

            suffix = Path(urlparse(image_url).path).suffix or ".jpg"
            image_path = IMAGES_DIR / f"{names[i]}{suffix}"

            try:
                if not image_path.exists():
                    response = client.get(image_url)
                    response.raise_for_status()
                    image_path.write_bytes(response.content)
                    time.sleep(IMG_DELAY)
            except Exception as e:
                print(f"Картинка {i} недоступна для скачивания: {image_url} ({e})")
                continue

            image_files.append(str(image_path.relative_to(BASE_DIR)))
            indexes.append(i)

    print(f"Скачано картинок: {len(image_files)} из {len(image_urls)} -> {IMAGES_DIR.relative_to(BASE_DIR)}/")
    return pd.Series(image_files, index=indexes, dtype="object")

def convert_column_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["price"] = pd.to_numeric(df["price"], errors="coerce").astype("Int64")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").astype("Int64")
    df["in_stock"] = df["in_stock"].astype(bool)

    for col in ["brand", "category"]:
        df[col] = df[col].astype("category")

    return df

def scrape() -> pd.DataFrame:
    all_rows: list[dict] = []

    with httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        for page in range(1, MAX_PAGES + 1):
            url = URL + CATALOG_PATH + (f"?page={page}" if page > 1 else "")
            response = client.get(url)
            response.raise_for_status()

            products = get_products(response.text)
            if not products:
                print(f"Страница {page}: товары не найдены, останавливаемся")
                break

            page_rows = [r for r in (extract_row(p) for p in products) if r]
            all_rows.extend(page_rows)
            print(f"Страница {page}: получено {len(page_rows)} товаров, всего {len(all_rows)}")

            if len(products) < 20:
                break

            time.sleep(DELAY)

    df = pd.DataFrame(all_rows)
    df = df.drop_duplicates(subset="sku").reset_index(drop=True)
    df = convert_column_types(df)

    print("\nСкачиваем фото товаров...")
    df["image_file"] = download_images(df["image_url"], df["sku"])

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False)
    print(f"\nДатасет сохранен: {OUT_FILE.relative_to(BASE_DIR)}")

    return df


if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 28)   # длинные описания и ссылки обрезаем

    df = scrape()

    print(f"\nРазмер датасета: {df.shape[0]} строк, {df.shape[1]} столбцов")
    print("\nТипы колонок:")
    print(df.dtypes.to_string())
    print("\nПервые 20 строк:")
    print(df.head(20))
