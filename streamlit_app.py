import streamlit as st
import pandas as pd
import numpy as np
import requests
from textblob import TextBlob
import matplotlib.pyplot as plt
import re
from youtube_transcript_api import YouTubeTranscriptApi

# ---------------------------------------------------------
# PAGE SETTINGS
# ---------------------------------------------------------
st.set_page_config(page_title="YouTube Comment Sentiment Analyzer", layout="wide")
st.title("📊 YouTube Comment Sentiment Analyzer")

# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------
api_key = st.text_input("🔑 Enter Your YouTube API Key", type="password")
video_url = st.text_input("🎥 Enter YouTube Video URL")

if st.button("Fetch & Analyze Video"):
    if not api_key or not video_url:
        st.error("Please provide BOTH an API key and a YouTube video URL.")
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

    video_meta_response = requests.get(video_meta_url, params=video_meta_params)
    video_meta = video_meta_response.json()

    if "items" not in video_meta or len(video_meta["items"]) == 0:
        st.error("Could not fetch video metadata.")
        st.stop()

    snippet = video_meta["items"][0]["snippet"]
    stats = video_meta["items"][0]["statistics"]

    title = snippet.get("title", "Unknown Title")
    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0))
    comments_count = int(stats.get("commentCount", 0))
    channel_id = snippet.get("channelId")

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
    st.subheader("📌 Video KPIs")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Views", f"{views:,}")
    k2.metric("Likes", f"{likes:,}")
    k3.metric("Comments", f"{comments_count:,}")
    k4.metric("Subscribers", f"{subs:,}")

    # Engagement Rate (simple)
    er = (likes + comments_count) / max(views, 1)
    k5.metric("Engagement Rate", f"{er:.2%}")

    # Display video info
    st.subheader("🎬 Video Information")
    st.image(thumbnail_url, width=450)
    st.write(f"**📌 Title:** {title}")

    # ---------------------------------------------------------
    # FETCH 10 MOST RECENT VIDEOS FROM CHANNEL
    # ---------------------------------------------------------
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": 10,
        "order": "date",
        "key": api_key
    }

    recent = requests.get(search_url, params=search_params).json()
    video_ids_recent = [i["id"].get("videoId") for i in recent["items"] if i["id"].get("videoId")]

    # Fetch stats for these videos
    stats_url = "https://www.googleapis.com/youtube/v3/videos"
    stats_params = {
        "part": "statistics,snippet",
        "id": ",".join(video_ids_recent),
        "key": api_key
    }

    recent_stats = requests.get(stats_url, params=stats_params).json()

    recent_titles = []
    recent_views = []

    for v in recent_stats["items"]:
        recent_titles.append(v["snippet"]["title"])
        recent_views.append(int(v["statistics"].get("viewCount", 0)))

    # ---------------------------------------------------------
    # RECENT VIDEOS VIEW COMPARISON CHART
    # ---------------------------------------------------------
    st.subheader("📈 Recent Video Performance (View Comparison)")

    fig_cmp, ax_cmp = plt.subplots(figsize=(10, 4))
    ax_cmp.plot(recent_titles, recent_views, marker='o')
    ax_cmp.axhline(views, linestyle="--", linewidth=2)

    ax_cmp.set_title("View Counts of Last 10 Videos")
    ax_cmp.set_ylabel("Views")
    ax_cmp.set_xticklabels(recent_titles, rotation=45, ha="right")

    st.pyplot(fig_cmp)

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

    response = requests.get(comments_url, params=params)
    data = response.json()

    comments = [
        item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        for item in data.get("items", [])
    ]

    if not comments:
        st.warning("No comments found.")
        st.stop()

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
            sentiment_labels.append("Negative")
        else:
            sentiment_labels.append("Neutral")

    df = pd.DataFrame({
        "comment": comments,
        "polarity": polarity_scores,
        "sentiment": sentiment_labels
    })

    st.subheader("🧾 Full Comment Dataset")
    st.dataframe(df)

    # ---------------------------------------------------------
    # VISUALIZATIONS
    # ---------------------------------------------------------
    st.subheader("📊 Comment Sentiment Visualizations")

    col1, col2 = st.columns(2)

    # SENTIMENT COUNTS
    with col1:
        fig1, ax1 = plt.subplots()
        sentiment_counts = df["sentiment"].value_counts()
        colors = {"Positive": "green", "Neutral": "gray", "Negative": "red"}
        sentiment_counts.plot(kind="bar", color=[colors[s] for s in sentiment_counts.index], ax=ax1)
        ax1.set_title("Sentiment Distribution")
        ax1.tick_params(axis='x', rotation=0)
        st.pyplot(fig1)

    # POLARITY HISTOGRAM
    with col2:
        fig2, ax2 = plt.subplots()
        vals = df["polarity"].dropna().values
        counts, bin_edges = np.histogram(vals, bins=20, range=(-1, 1))

        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        norm_centers = (bin_centers + 1) / 2
        cmap = plt.get_cmap("RdYlGn")
        bar_colors = [cmap(n) for n in norm_centers]

        ax2.bar(bin_centers, counts, width=(bin_edges[1] - bin_edges[0]), color=bar_colors, edgecolor="black")
        ax2.set_title("Polarity Distribution")
        st.pyplot(fig2)

    # ---------------------------------------------------------
    # TOP 10 POSITIVE & NEGATIVE
    # ---------------------------------------------------------
    st.subheader("🏆 Top Comments")

    col3, col4 = st.columns(2)

    with col3:
        st.write("### 🌟 Top 10 Most Positive Comments")
        st.table(df.sort_values(by="polarity", ascending=False).head(10)[["comment", "polarity"]])

    with col4:
        st.write("### 💀 Top 10 Most Negative Comments")
        st.table(df.sort_values(by="polarity", ascending=True).head(10)[["comment", "polarity"]])

    # ---------------------------------------------------------
    # TRANSCRIPT SENTIMENT TIMELINE
    # ---------------------------------------------------------
    st.subheader("🎬 Sentiment Throughout the Video (Transcript)")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        times = []
        sentiments = []

        for t in transcript:
            times.append(t["start"] / 60)
            sentiments.append(TextBlob(t["text"]).sentiment.polarity)

        trans_df = pd.DataFrame({"time_min": times, "polarity": sentiments})

        fig_t, ax_t = plt.subplots(figsize=(10, 4))
        ax_t.plot(trans_df["time_min"], trans_df["polarity"], linewidth=2)
        ax_t.axhline(0, color="black", linestyle="--")
        ax_t.set_title("Sentiment Over Video Timeline")
        ax_t.set_xlabel("Time (minutes)")
        ax_t.set_ylabel("Sentiment Polarity (-1 to 1)")
        st.pyplot(fig_t)

    except Exception as e:
        st.warning(f"Transcript not available: {e}")

    # ---------------------------------------------------------
    # DOWNLOAD CSV
    # ---------------------------------------------------------
    st.subheader("⬇️ Download Results")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="youtube_sentiment_results.csv",
        mime="text/csv"
    )
