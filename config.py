import os
import json


class Config(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config_path = "raw/config.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, "r") as f:
                config_ = json.load(f)
                self.update(config_)
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            pass
        self.config_path = config_path

    def save(self):
        with open(self.config_path, "w") as g:
            json.dump(self, g, indent=4)


config = Config()
