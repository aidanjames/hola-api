import requests
from bs4 import BeautifulSoup


class StoryManager:

    def __init__(self):
        self.titles = ["perro-aterrado"]
        self.base_url = "https://www.mundoprimaria.com/cuentos-infantiles-cortos/cuentos-populares/"

    def fetch_story(self, story):
        if story is None:
            story = self.titles[0]
        web_site_html = requests.get(self.base_url + story)
        soup = BeautifulSoup(web_site_html.text, "html.parser")

        title = soup.find(name="h1", class_="text-center").getText()
        text = [paragraph.getText() for paragraph in soup.find_all(name="p",
                                                                   style=["text-align: justify;",
                                                                          "text-align: justify; padding-left: 40px;"])]

        return title, text
