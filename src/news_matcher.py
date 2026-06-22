from __future__ import annotations

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# News loading
# ---------------------------------------------------------------------------

def load_news_events(news_path: str | Path) -> pd.DataFrame:
    """
    Load a local news/events CSV file.

    Supported formats:

    Option 1:
        datetime, headline, event_type, importance, source, url

    Option 2:
        date, time, headline, event_type, importance, source, url
    """

    news_path = Path(news_path)

    if not news_path.exists():
        raise FileNotFoundError(f"News file not found: {news_path}")

    news_df = pd.read_csv(news_path)

    if "datetime" in news_df.columns:
        news_df["event_datetime"] = pd.to_datetime(
            news_df["datetime"],
            utc=True,
            errors="coerce",
        )

    elif "date" in news_df.columns and "time" in news_df.columns:
        news_df["event_datetime"] = pd.to_datetime(
            news_df["date"].astype(str) + " " + news_df["time"].astype(str),
            utc=True,
            errors="coerce",
        )

    elif "date" in news_df.columns:
        news_df["event_datetime"] = pd.to_datetime(
            news_df["date"],
            utc=True,
            errors="coerce",
        )

    else:
        raise ValueError(
            "News CSV must contain either 'datetime', 'date + time', or 'date' columns."
        )

    news_df = news_df.dropna(subset=["event_datetime"])
    news_df = news_df.sort_values("event_datetime").reset_index(drop=True)

    optional_columns = [
        "headline",
        "event_type",
        "importance",
        "source",
        "url",
        "symbol",
    ]

    for column in optional_columns:
        if column not in news_df.columns:
            news_df[column] = ""

    return news_df


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_news_to_jumps(
    jump_df: pd.DataFrame,
    news_df: pd.DataFrame,
    window_minutes: int = 30,
) -> pd.DataFrame:
    """
    Match news/events to volatility jumps within a time window.

    This does not prove the news caused the jump.
    It only shows events near the jump time.
    """

    if jump_df.empty or news_df.empty:
        return pd.DataFrame()

    jumps = jump_df.copy()
    news = news_df.copy()

    jumps["datetime"] = pd.to_datetime(
        jumps["datetime"],
        utc=True,
        errors="coerce",
    )

    news["event_datetime"] = pd.to_datetime(
        news["event_datetime"],
        utc=True,
        errors="coerce",
    )

    jumps = jumps.dropna(subset=["datetime"])
    news = news.dropna(subset=["event_datetime"])

    window = pd.Timedelta(minutes=window_minutes)

    matches = []

    for _, jump_row in jumps.iterrows():
        jump_time = jump_row["datetime"]

        nearby_news = news[
            (news["event_datetime"] >= jump_time - window)
            & (news["event_datetime"] <= jump_time + window)
        ].copy()

        for _, news_row in nearby_news.iterrows():
            minutes_from_jump = (
                news_row["event_datetime"] - jump_time
            ).total_seconds() / 60

            matches.append(
                {
                    "jump_datetime": jump_time,
                    "event_datetime": news_row["event_datetime"],
                    "minutes_from_jump": minutes_from_jump,
                    "jump_score": jump_row.get("jump_score"),
                    "jump_regime": jump_row.get("jump_regime"),
                    "headline": news_row.get("headline", ""),
                    "event_type": news_row.get("event_type", ""),
                    "importance": news_row.get("importance", ""),
                    "source": news_row.get("source", ""),
                    "url": news_row.get("url", ""),
                    "symbol": news_row.get("symbol", ""),
                }
            )

    matches_df = pd.DataFrame(matches)

    if matches_df.empty:
        return matches_df

    matches_df = matches_df.sort_values(
        ["jump_datetime", "minutes_from_jump"],
        key=lambda column: column.abs() if column.name == "minutes_from_jump" else column,
    ).reset_index(drop=True)

    return matches_df


def match_news_to_jumps_from_csv(
    jump_df: pd.DataFrame,
    news_path: str | Path,
    window_minutes: int = 30,
) -> pd.DataFrame:
    """
    Load a news CSV and match it to volatility jumps.
    """

    news_df = load_news_events(news_path)

    return match_news_to_jumps(
        jump_df=jump_df,
        news_df=news_df,
        window_minutes=window_minutes,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_news_matches_table(matches_df: pd.DataFrame) -> pd.DataFrame:
    """
    Make news matches easier to read.
    """

    if matches_df.empty:
        return matches_df.copy()

    columns = [
        "jump_datetime",
        "event_datetime",
        "minutes_from_jump",
        "jump_score",
        "jump_regime",
        "headline",
        "event_type",
        "importance",
        "source",
        "symbol",
        "url",
    ]

    available_columns = [
        column for column in columns
        if column in matches_df.columns
    ]

    output = matches_df[available_columns].copy()

    round_columns = {
        "minutes_from_jump": 1,
        "jump_score": 2,
    }

    for column, decimals in round_columns.items():
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce").round(decimals)

    output = output.rename(
        columns={
            "jump_datetime": "Jump Datetime",
            "event_datetime": "Event Datetime",
            "minutes_from_jump": "Minutes From Jump",
            "jump_score": "Jump Score",
            "jump_regime": "Jump Regime",
            "headline": "Headline",
            "event_type": "Event Type",
            "importance": "Importance",
            "source": "Source",
            "symbol": "Symbol",
            "url": "URL",
        }
    )

    return output


def print_news_matches(matches_df: pd.DataFrame) -> None:
    """
    Print matched news/events.
    """

    if matches_df.empty:
        print("No related news/events found near the selected jumps.")
        return

    friendly_table = format_news_matches_table(matches_df)

    print("Related News / Events")
    print("These events happened near volatility jumps. This does not prove causation.")
    print()
    print(friendly_table.to_string(index=False))