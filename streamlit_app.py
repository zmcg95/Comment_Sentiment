import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
from textblob import TextBlob
import matplotlib.pyplot as plt
from youtube_transcript_api import YouTubeTranscriptApi

# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(page_title="YouTube Sentiment Analyzer", layout="wide")
st.title("📊 YouTube Comment & Transcript Sentiment Analyzer")


# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------
api_key = st.text_input("🔑 Enter Your YouTube API Key", type="password")
video_url = st.text_input("🎥 Enter YouTube Video URL")

if st.button("Fetch & Analyze"):
    if not api_key or not video_url:
        st.error("Please provide BOTH API key and YouTube URL.")
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
    video_meta_url = "https://www.googleapis.com/youtube/v3/videos"
    video_meta_params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }

    video_meta = requests.get(video_meta_url, params=video_meta_params).json()

    if "items" not in video_meta or len(video_meta["items"]) == 0:
        st.error("Failed to fetch video metadata.")
        st.stop()

    snippet = video_meta["items"][0]["snippet"]
    stats = video_meta["items"][0]["statistics"]

    title = snippet.get("title", "Unknown Title")
    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0)) if "likeCount" in stats else 0
    comments_count = int(stats.get("commentCount", 0)) if "commentCount" in stats else 0
    channel_id = snippet["channelId"]
    channel_title = snippet["channelTitle"]

    engagement_rate = round(((likes + comments_count) / views) * 100, 2) if views > 0 else 0

    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # ---------------------------------------------------------
    # FETCH CHANNEL SUBSCRIBERS
    # ---------------------------------------------------------
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_params = {
        "part": "statistics",
        "id": channel_id,
        "key": api_key
    }

    channel_data = requests.get(channel_url, params=channel_params).json()
    subs = int(channel_data["items"][0]["statistics"].get("subscriberCount", 0))

    # ---------------------------------------------------------
    # KPI CARDS
    # ---------------------------------------------------------
    colA, colB, colC, colD, colE = st.columns(5)

    colA.metric("📺 Views", f"{views:,}")
    colB.metric("👍 Likes", f"{likes:,}")
    colC.metric("💬 Comments", f"{comments_count:,}")
    colD.metric("📊 Engagement Rate", f"{engagement_rate}%")
    colE.metric("👤 Subscribers", f"{subs:,}")

    # Display thumbnail + title
    st.image(thumbnail_url, width=450)
    st.subheader(f"🎬 {title}")
    st.write(f"📺 Channel: **{channel_title}**")

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

    data = requests.get(comments_url, params=params).json()

    comments = []
    for item in data.get("items", []):
        comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        comments.append(comment)

    st.success(f"Fetched {len(comments)} comments!")

    # ---------------------------------------------------------
    # SENTIMENT ANALYSIS (COMMENTS)
    # ---------------------------------------------------------
    polarity_scores = []
    sentiment_labels = []

    for c in comments:
        polarity = TextBlob(c).sentiment.polarity
        polarity_scores.append(polarity)

        if polarity > 0.05:
            sentiment_labels.append("Positive")
        elif polarity < -0.05:
            sentiment_labels.append("Negative")
        else:
            sentiment_labels.append("Neutral")

    df = pd.DataFrame({
        "comment": comments,
        "polarity": polarity_scores,
        "sentiment": sentiment_labels
    })

    # ---------------------------------------------------------
    # VISUALS: SENTIMENT + POLARITY
    # ---------------------------------------------------------
    st.subheader("📈 Comment Sentiment Visuals")
    col1, col2 = st.columns(2)

    # ---- Sentiment bar chart ----
    with col1:
        fig1, ax1 = plt.subplots()
        counts = df["sentiment"].value_counts()
        colors = {"Positive": "green", "Neutral": "gray", "Negative": "red"}

        counts.plot(kind="bar", ax=ax1, color=[colors[x] for x in counts.index])
        ax1.set_title("Sentiment Distribution")
        st.pyplot(fig1)

    # ---- Polarity histogram (red → green) ----
    with col2:
        fig2, ax2 = plt.subplots()
        vals = df["polarity"].values

        bins = 20
        counts, edges = np.histogram(vals, bins=bins, range=(-1, 1))
        centers = (edges[:-1] + edges[1:]) / 2
        norm = (centers + 1) / 2
        cmap = plt.get_cmap("RdYlGn")
        colors = [cmap(n) for n in norm]

        ax2.bar(centers, counts, width=0.09, color=colors, edgecolor="black")
        ax2.set_title("Polarity Distribution")
        st.pyplot(fig2)

    # ---------------------------------------------------------
    # TOP 10 POSITIVE / NEGATIVE (TABLES)
    # ---------------------------------------------------------
    st.subheader("🏆 Top Comments")

    top_pos = df.sort_values("polarity", ascending=False).head(10).reset_index(drop=True)
    top_neg = df.sort_values("polarity", ascending=True).head(10).reset_index(drop=True)

    col3, col4 = st.columns(2)

    with col3:
        st.write("### 🌟 Top 10 Positive")
        st.table(top_pos)

    with col4:
        st.write("### 💀 Top 10 Negative")
        st.table(top_neg)

    # ---------------------------------------------------------
    # LAST 10 VIDEOS (VIEWS CHART)
    # ---------------------------------------------------------
    st.subheader("📊 Recent Channel Video Performance")

    uploads_url = "https://www.googleapis.com/youtube/v3/search"
    uploads_params = {
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": 10,
        "order": "date",
        "key": api_key
    }

    recent = requests.get(uploads_url, params=uploads_params).json()

    video_ids = [x["id"]["videoId"] for x in recent.get("items", []) if "videoId" in x["id"]]

    vid_views = []
    for vid in video_ids:
        meta = requests.get(video_meta_url, params={"part": "statistics", "id": vid, "key": api_key}).json()
        v = int(meta["items"][0]["statistics"]["viewCount"])
        vid_views.append(v)

    fig3, ax3 = plt.subplots()
    ax3.plot(range(len(vid_views)), vid_views, marker="o", label="Recent Videos")
    ax3.axhline(y=views, color="red", linestyle="--", label="Current Video")
    ax3.set_title("Views of Last 10 Videos")
    ax3.legend()
    st.pyplot(fig3)

    # ---------------------------------------------------------
    # TRANSCRIPT SENTIMENT OVER TIME
    # ---------------------------------------------------------
    st.subheader("🕒 Transcript Sentiment Over Time")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        times = [t["start"] for t in transcript]
        texts = [t["text"] for t in transcript]

        transcript_polarity = [TextBlob(t).sentiment.polarity for t in texts]

        fig4, ax4 = plt.subplots(figsize=(10, 4))
        ax4.plot(times, transcript_polarity, color="purple")
        ax4.set_title("Sentiment Across Video Timeline")
        ax4.set_xlabel("Time (seconds)")
        ax4.set_ylabel("Polarity")
        st.pyplot(fig4)

    except Exception as e:
        st.warning("No transcript available for this video.")

    # ---------------------------------------------------------
    # DOWNLOAD CSV
    # ---------------------------------------------------------
    st.subheader("⬇️ Download Comments CSV")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "youtube_comments_sentiment.csv", "text/csv")
