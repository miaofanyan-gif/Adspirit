# TODO: replace with a real TikTok scraper (search by product keywords derived
# from state["product_url"], return the top 4-5 popular related videos).
def run(state: dict) -> dict:
    videos = [
        {"source_url": f"https://www.tiktok.com/@mock/video/{i}", "platform": "tiktok"}
        for i in range(1, 6)
    ]
    return {"videos": videos, "mock": True}
