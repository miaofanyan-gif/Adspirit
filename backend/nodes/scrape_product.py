# TODO: replace with a real TikTok Shop product-page scraper for
# state["product_url"] (title, price, description, images).
def run(state: dict) -> dict:
    product = {
        "title": "Mock Product Title",
        "price": None,
        "description": "TODO: scrape real product description",
        "images": [],
        "mock": True,
    }
    return {"product": product}
