"""Display-name overrides for cohorts.

Cohort names in BigQuery are long and contain special characters. This
module maps each raw `cohort_name` to a friendlier display name used in
the sidebar dropdown, page header, and share URL. Cohorts that aren't
listed here fall back to their raw name.
"""

from __future__ import annotations


# raw cohort_name → friendly display name
COHORT_ALIAS: dict[str, str] = {
    "app:WBS-standalone":                              "WBSStandalone",
    "app:english_bangla-standalone":                   "EnglishBanglaStandalone",
    "app:hausa-standalone":                            "HausaStandalone",
    "app:lungelo_zulu_english-standalone":             "LungeloZuluEnglishStandalone",
    "app:maharishi-standalone":                        "MaharishiStandalone",
    "app:nairobimomone_swahili_english-standalone":    "njeri",
    "app:nairobimomtwo_swahili_english-standalone":    "laureen",
    "app:nairobimomthree_swahili_english-standalone":  "njambi",
    "program:Congo - Brazzaville":                     "CongoBrazzaville",
    "program:Durban Cohort":                           "DurbanCohort",
    "program:WBS - Nigeria":                           "WBSNigeria",
}


def display_name(raw: str) -> str:
    alias = COHORT_ALIAS.get(raw, "").strip()
    return alias or raw


def cohort_for_display(value: str, all_cohorts: list[str]) -> str | None:
    """Reverse lookup used to resolve a URL `?cohort=` value to a raw cohort_name.

    Matches against the display name first; falls back to the raw name so
    pre-alias share URLs keep working.
    """
    for raw in all_cohorts:
        if display_name(raw) == value:
            return raw
    if value in all_cohorts:
        return value
    return None
