import json


class FileManager:

    def check_for_existing_translation(self, text, title):
        file_path = f"Files/{title}.txt"
        try:
            with open(file_path) as file:
                data = json.load(file)
                text = [paragraph["en"] for paragraph in data["content"] if paragraph["es"] == text][0]
                return text
        except FileNotFoundError:
            return None
        except KeyError:
            return None
        except IndexError:
            return None

    def save_new_translation(self, translation, title):
        file_path = f"Files/{title}.txt"
        new_object = {
            "es": translation[0],
            "en": translation[1]
        }
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            with open(file_path, "w") as file:
                initial_json = {
                    "content": [
                        new_object
                    ]
                }
                json.dump(initial_json, file)
        else:
            with open(file_path, "w") as file:
                data["content"].append(new_object)
                json.dump(data, file)

    def return_story(self, title):
        file_path = f"Files/{title}.txt"
        try:
            with open(file_path) as file:
                data = json.load(file)
                spanish = [paragraph["es"] for paragraph in data["content"]]
                english = [paragraph["en"] for paragraph in data["content"]]
                final_str = ""
                final_str += "********* SPANISH *********\n"
                for i in range(len(spanish)):
                    final_str += f"{spanish[i]}\n"
                final_str += "********* ENGLISH *********\n"
                for i in range(len(english)):
                    final_str += f"{english[i]}\n"
                return final_str
        except FileNotFoundError:
            return None
        except KeyError:
            return None
        except IndexError:
            return None
