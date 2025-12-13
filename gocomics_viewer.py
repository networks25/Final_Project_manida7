import os
import re
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from PIL import Image, ImageTk

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
IMAGE_DIR = "downloaded_comics"


class ComicScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        if not os.path.exists(IMAGE_DIR):
            os.makedirs(IMAGE_DIR)

    def fetch_comic_page(self, url: str):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"Error fetching page: {e}")
            return None

    def _abs_url(self, u: str | None):
        """Make a GoComics-relative URL absolute."""
        if not u:
            return None
        if u.startswith("http://") or u.startswith("https://"):
            return u
        if u.startswith("/"):
            return "https://www.gocomics.com" + u
        return "https://www.gocomics.com/" + u.lstrip("/")

    def parse_comic(self, html: str):
        soup = BeautifulSoup(html, "html.parser")

        img_url = None

        og_img = soup.find("meta", attrs={"property": "og:image"})
        if og_img and og_img.get("content"):
            img_url = og_img["content"]

        if not img_url:
            img_tag = soup.find(
                "img",
                src=re.compile(
                    r"(assets\.amuniversal\.com|featureassets\.gocomics\.com)"
                ),
            )
            if img_tag and img_tag.get("src"):
                img_url = img_tag["src"]

        prev_url = None
        next_url = None

        link_prev = soup.find("a", rel=lambda v: v and "prev" in v.lower())
        link_next = soup.find("a", rel=lambda v: v and "next" in v.lower())

        if link_prev and link_prev.get("href"):
            prev_url = link_prev["href"]
        if link_next and link_next.get("href"):
            next_url = link_next["href"]

        if not (prev_url and next_url):
            for a in soup.find_all("a"):
                text = a.get_text(strip=True).lower()
                if "previous" == text or text.startswith("previous "):
                    if not prev_url and a.get("href"):
                        prev_url = a["href"]
                elif "next" == text or text.startswith("next "):
                    if not next_url and a.get("href"):
                        next_url = a["href"]
                if prev_url and next_url:
                    break

        prev_url = self._abs_url(prev_url)
        next_url = self._abs_url(next_url)

        return img_url, prev_url, next_url

    def download_image(self, img_url: str | None):
        if not img_url:
            return None
        try:
            img_name = img_url.split("/")[-1].split("?")[0]
            img_path = os.path.join(IMAGE_DIR, img_name)
            if not os.path.exists(img_path):
                resp = requests.get(img_url, headers=HEADERS, timeout=10)
                resp.raise_for_status()
                with open(img_path, "wb") as f:
                    f.write(resp.content)
            return img_path
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None

    def get_comic(self, url: str):
        html = self.fetch_comic_page(url)
        if not html:
            return None, None, None, None

        img_url, prev_url, next_url = self.parse_comic(html)
        img_path = self.download_image(img_url) if img_url else None
        return img_path, img_url, prev_url, next_url


class ComicViewer:
    def __init__(self, root, start_url: str):
        self.root = root
        self.scraper = ComicScraper(start_url)
        self.current_url = start_url

        self.img_label = tk.Label(root)
        self.img_label.pack(padx=10, pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack()

        self.prev_btn = tk.Button(
            btn_frame, text="⏮ Previous", command=self.show_prev
        )
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(
            btn_frame, text="Next ⏭", command=self.show_next
        )
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.status = tk.Label(root, text="", fg="gray")
        self.status.pack()

        self.prev_url = None
        self.next_url = None

        self.show_comic(self.current_url)

    def show_comic(self, url: str):
        self.status.config(text="Loading...")
        self.root.update()

        img_path, img_url, prev_url, next_url = self.scraper.get_comic(url)

        if img_path and os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((900, 600))
                self.photo = ImageTk.PhotoImage(img)
                self.img_label.config(image=self.photo, text="")
                self.img_label.image = self.photo
                self.status.config(text=img_url or url)
            except Exception as e:
                self.img_label.config(image="", text="Error loading image")
                self.status.config(text=f"Image error: {e}")
        else:
            self.img_label.config(image="", text="Comic not found")
            self.status.config(text="Comic not found or network error.")

        self.prev_url = prev_url
        self.next_url = next_url
        self.prev_btn.config(state=tk.NORMAL if prev_url else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if next_url else tk.DISABLED)
        self.current_url = url

    def show_prev(self):
        if self.prev_url:
            self.show_comic(self.prev_url)

    def show_next(self):
        if self.next_url:
            self.show_comic(self.next_url)


def main():
    start_url = input(
        "Enter GoComics URL (e.g., https://www.gocomics.com/pearlsbeforeswine): "
    ).strip()

    if "gocomics.com" not in start_url or not start_url.startswith("http"):
        print("Please enter a valid GoComics URL.")
        return

    root = tk.Tk()
    root.title("GoComics.com Comic Viewer")
    root.geometry("950x700")
    ComicViewer(root, start_url)
    root.mainloop()


if __name__ == "__main__":
    main()

