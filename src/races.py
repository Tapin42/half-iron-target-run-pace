from dataclasses import dataclass
import os


@dataclass(frozen=True)
class RaceConfig:
    slug: str
    display_name: str
    event_key: str
    search_category: str | None = None
    finish_split: str = "FINISH"


def load_race_configs() -> dict[str, RaceConfig]:
    rockford = RaceConfig(
        slug="rockford-70.3",
        display_name="Ironman 70.3 Rockford",
        event_key=os.getenv("RTRT_EVENT_KEY", "IRM-ROCKFORD703-2026"),
        search_category=os.getenv("RTRT_SEARCH_CATEGORY"),
        finish_split=os.getenv("RTRT_FINISH_SPLIT", "FINISH"),
    )
    venice = RaceConfig(
        slug="venice-70.3",
        display_name="Ironman 70.3 Venice",
        event_key="IRM-VENICE703-2026",
        search_category=os.getenv("RTRT_VENICE_SEARCH_CATEGORY"),
        finish_split=os.getenv("RTRT_VENICE_FINISH_SPLIT", "FINISH"),
    )
    da_nang = RaceConfig(
        slug="da-nang-70.3",
        display_name="Ironman 70.3 Da Nang",
        event_key="IRM-VIETNAM-2026",
        search_category=os.getenv("RTRT_DA_NANG_SEARCH_CATEGORY"),
        finish_split=os.getenv("RTRT_DA_NANG_FINISH_SPLIT", "FINISH"),
    )
    return {
        rockford.slug: rockford,
        venice.slug: venice,
        da_nang.slug: da_nang,
    }
