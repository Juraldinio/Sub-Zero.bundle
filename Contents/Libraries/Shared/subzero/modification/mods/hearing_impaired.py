# coding=utf-8
import re

from subzero.modification.mods import SubtitleTextModification
from subzero.modification.processors.re_processor import NReProcessor
from subzero.modification import registry


class HearingImpaired(SubtitleTextModification):
    identifier = "remove_HI"
    description = "Remove Hearing Impaired tags"
    exclusive = True

    long_description = """\
    Removes tags, text and characters from subtitles that are meant for hearing impaired people
    """

    processors = [
        # brackets
        NReProcessor(re.compile(r'(?sux)[([].+[)\]]'), "", name="HI_brackets"),

        # text before colon (and possible dash in front), max 11 chars after the first whitespace (if any)
        NReProcessor(re.compile(r'(?u)(^[A-z\-\'"_]+[\w\s]{0,11}:[^0-9{2}][\s]*)'), "", name="HI_before_colon"),

        # all caps line (at least 3 chars)
        NReProcessor(re.compile(r'(?u)(^[A-Z]{3,}$)'), "", name="HI_all_caps"),

        # dash in front
        # NReProcessor(re.compile(r'(?u)^\s*-\s*'), "", name="HI_starting_dash"),
    ]


registry.register(HearingImpaired)
