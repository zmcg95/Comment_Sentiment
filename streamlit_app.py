import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re

# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(page_title="YouTube Sentiment Analyzer", layout="wide")
st.title("📊 YouTube Sentiment Analyzer")

# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------
api_key = st.text_input("🔑 Enter Your YouTube API Key", type="password")
video_url = st.text_input("🎥 Enter YouTube Video URL")

if st.button("Fetch & Analyze"):
    if not api_key or not video_url:
        st.error("Please provide BOTH an API key and a YouTube URL.")
        st.stop()

    # Extract video ID
    match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if not match:
        st.error("Invalid YouTube URL format.")
        st.stop()
    video_id = match.group(1)

    # ---------------------------------------------------------
    # FETCH VIDEO METADATA
    # ---------------------------------------------------------
    meta_url = "https://www.googleapis.com/youtube/v3/videos"
    meta_params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    meta = requests.get(meta_url, params=meta_params).json()

    if "items" not in meta or len(meta["items"]) == 0:
        st.error("Video not found or API error.")
        st.stop()

    snippet = meta["items"][0]["snippet"]
    stats = meta["items"][0]["statistics"]

    title = snippet["title"]
    views = int(stats.get("viewCount", 0))
    channel_id = snippet["channelId"]
    channel_title = snippet["channelTitle"]
    thumbnail = snippet["thumbnails"]["high"]["url"]

    # ---------------------------------------------------------
    # FETCH CHANNEL DATA (SUBSCRIBERS)
    # ---------------------------------------------------------
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_params = {
        "part": "statistics",
        "id": channel_id,
        "key": api_key
    }
    channel_info = requests.get(channel_url, params=channel_params).json()
    subs = int(channel_info["items"][0]["statistics"]["subscriberCount"])

    # ---------------------------------------------------------
    # KPI METRICS
    # ---------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Video Title", title)
    col2.metric("Channel", channel_title)
    col3.metric("Views", f"{views:,}")
    col4.metric("Subscribers", f"{subs:,}")

    st.image(thumbnail, width=400)

    # ---------------------------------------------------------
    # FETCH COMMENTS
    # ---------------------------------------------------------
    comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText"
    }

    comment_data = requests.get(comments_url, params=params).json()

    comments = []
    polarities = []
    sentiments = []

    for item in comment_data.get("items", []):
        c = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        polarity = TextBlob(c).sentiment.polarity

        if polarity > 0.1:
            sentiment = "Positive"
        elif polarity < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        comments.append(c)
        polarities.append(polarity)
        sentiments.append(sentiment)

    df = pd.DataFrame({
        "comment": comments,
        "polarity": polarities,
        "sentiment": sentiments
    })

    st.success(f"Fetched {len(df)} comments!")
    st.dataframe(df)

    # ---------------------------------------------------------
    # SENTIMENT BAR CHART
    # ---------------------------------------------------------
    st.subheader("📊 Sentiment Distribution")
    fig1, ax1 = plt.subplots()
    counts = df["sentiment"].value_counts()
    ax1.bar(counts.index, counts.values, color=["green", "grey", "red"])
    st.pyplot(fig1)

    # ---------------------------------------------------------
    # POLARITY HISTOGRAM (RED → GREEN)
    # ---------------------------------------------------------
    st.subheader("📈 Polarity Distribution")
    fig2, ax2 = plt.subplots()
    bins = np.linspace(-1, 1, 20)
    cmap = plt.get_cmap("RdYlGn")
    colors = [cmap((p + 1) / 2) for p in df["polarity"]]

    ax2.bar(range(len(df)), df["polarity"], color=colors)
    ax2.axhline(0, linestyle="--", color="black")
    st.pyplot(fig2)

    # ---------------------------------------------------------
    # TOP COMMENTS (NO INDEX)
    # ---------------------------------------------------------
    st.subheader("🌟 Top 10 Positive Comments")
    st.table(df.sort_values("polarity", ascending=False).head(10)[["comment", "polarity"]])

    st.subheader("💀 Top 10 Negative Comments")
    st.table(df.sort_values("polarity", ascending=True).head(10)[["comment", "polarity"]])

    # ---------------------------------------------------------
    # FETCH TRANSCRIPT (AUTO-GENERATED INCLUDED)
    # ---------------------------------------------------------
    st.subheader("📜 Transcript Sentiment Over Time")

    def get_transcript(video_id):
        try:
            # Try normal English transcript first
            try:
                return YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            except:
                pass
            
            # Try all available transcripts
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            for t in transcripts:
                try:
                    return t.fetch()
                except:
                    continue

            return None

        except (TranscriptsDisabled, NoTranscriptFound):
            return None

    transcript = get_transcript(video_id)

    if transcript:
        times = [t["start"] for t in transcript]
        texts = [t["text"] for t in transcript]
        sentiments = [TextBlob(t).sentiment.polarity for t in texts]

        df_t = pd.DataFrame({"time": times, "sentiment": sentiments})

        fig3, ax3 = plt.subplots(figsize=(10, 4))
        ax3.plot(df_t["time"], df_t["sentiment"])
        ax3.axhline(0, linestyle="--", color="black")
        ax3.set_xlabel("Time (s)")
        ax3.set_ylabel("Sentiment")
        ax3.set_title("Sentiment Across the Video")
        st.pyplot(fig3)

    else:
        st.warning("No transcript available for this video.")

    # ---------------------------------------------------------
    # LAST 10 VIDEOS VIEW COMPARISON
    # ---------------------------------------------------------
    st.subheader("📈 Last 10 Videos View Comparison")

    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "maxResults": 10,
        "key": api_key
    }

    search_data = requests.get(search_url, params=search_params).json()
    recent_ids = [
        i["id"]["videoId"]
        for i in search_data.get("items", [])
        if i["id"]["kind"] == "youtube#video"
    ]

    view_list = []
    title_list = []

    for vid in recent_ids:
        vid_params = {
            "part": "snippet,statistics",
            "id": vid,
            "key": api_key
        }
        v = requests.get(meta_url, params=vid_params).json()
        if "items" in v and len(v["items"]) > 0:
            view_list.append(int(v["items"][0]["statistics"].get("viewCount", 0)))
            title_list.append(v["items"][0]["snippet"]["title"])

    fig4, ax4 = plt.subplots(figsize=(10, 5))
    ax4.plot(view_list, marker="o")
    ax4.axhline(views, color="red", linestyle="--", label="This Video Views")
    ax4.set_xticks(range(len(title_list)))
    ax4.set_xticklabels([t[:18] + "..." for t in title_list], rotation=45)
    ax4.set_ylabel("Views")
    ax4.legend()
    st.pyplot(fig4)
