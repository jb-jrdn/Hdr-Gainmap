from enum import Enum


class Preset(str, Enum):
    default = "default"
    best = "best"
    light = "light"
    insta = "insta"
