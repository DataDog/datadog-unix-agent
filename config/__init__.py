from config import Config
import default

config = Config()
default.init(config)

__all__ = ["Config", "config"]
