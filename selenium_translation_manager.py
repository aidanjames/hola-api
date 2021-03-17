from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import time
from file_manager import FileManager
import os


class SeleniumTranslationManger:

    def __init__(self):
        self.options = webdriver.ChromeOptions()
        self.options.binary_location = os.getenv("CHROME_BIN")
        self.options.add_argument('--headless')
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--no-sandbox")
        self.chrome_driver_path = os.getenv("CHROME_DRIVER_PATH")
        self.driver = None
        self.file_manager = FileManager()

    def translate(self, text, title):
        # The below is only used where we are saving translations to file (rather than database)

        # existing_translation = self.file_manager.check_for_existing_translation(text, title)
        # if existing_translation is not None:
        #     print("we already have it!")
        #     return existing_translation

        self.initialise_webdriver()
        self.driver.get(url=f"https://translate.google.com/?sl=es&tl=en&op=translate")

        original_text_element = self.driver.find_element_by_xpath(
            '//*[@id="yDmH0d"]/c-wiz/div/div[2]/c-wiz/div[2]/c-wiz/div[1]/div[2]/div[2]/c-wiz[1]/span/span/div/textarea')
        original_text_element.send_keys(text)

        waiting_for_text = True
        timeout = time.time() + 5

        while waiting_for_text and time.time() < timeout:
            try:
                translated_text = self.driver.find_element_by_xpath(
                    '//*[@id="yDmH0d"]/c-wiz/div/div[2]/c-wiz/div[2]/c-wiz/div[1]/div[2]/div[2]/c-wiz[2]/div['
                    '5]/div/div[3]/div[1]/div/div[1]/div[1]/textarea').get_attribute("data-initial-value")
                print(f"I've got a translation, which is... {translated_text}")

                # The below is only used where we are saving translations to file (rather than database)

                # self.file_manager.save_new_translation((text, translated_text), title)
                return translated_text
            except NoSuchElementException:
                pass
        return None

    def initialise_webdriver(self):
        if self.driver is None:
            self.driver = webdriver.Chrome(chrome_options=self.options, executable_path=self.chrome_driver_path)

    def close_webdriver(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
