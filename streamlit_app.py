import streamlit as st
import pandas as pd
import numpy as np
import requests
from textblob import TextBlob
import matplotlib.pyplot as plt
import re

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

if st.button("Fetch & Analyze Comments"):
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
    # FETCH VIDEO METADATA (Title, Views, Likes, Comment Count)
    # ---------------------------------------------------------
    video_meta_url = "https://www.googleapis.com/youtube/v3/videos"
    video_meta_params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }

    video_meta_response = requests.get(video_meta_url, params=video_meta_params)
    video_meta = video_meta_response.json()

    if "items" in video_meta and len(video_meta["items"]) > 0:
        snippet = video_meta["items"][0]["snippet"]
        stats = video_meta["items"][0]["statistics"]

        title = snippet.get("title", "Unknown Title")
        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comment_count = int(stats.get("commentCount", 0))

        engagement_rate = ((likes + comment_count) / max(views, 1)) * 100
        custom_score = round((engagement_rate * 0.6) + (likes * 0.002), 2)

        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

        # ---------------------------------------------------------
        # VIDEO HEADER
        # ---------------------------------------------------------
        st.subheader("🎬 Video Information")
        col_vid, col_meta = st.columns([1, 2])

        with col_vid:
            st.image(thumbnail_url, width=420)

        with col_meta:
            st.write(f"### {title}")

            # ------------- METRIC CARDS -------------
            m1, m2, m3 = st.columns(3)
            m1.metric("👁️ Views", f"{views:,}")
            m2.metric("👍 Likes", f"{likes:,}")
            m3.metric("💬 Comments", f"{comment_count:,}")

            m4, m5 = st.columns(2)
            m4.metric("📈 Engagement Rate", f"{engagement_rate:.2f}%")
            m5.metric("🔥 Custom Score", custom_score)

    else:
        st.warning("Could not fetch video metadata.")

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

    comments = []
    for item in data.get("items", []):
        comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        comments.append(comment)

    if not comments:
        st.warning("No comments found.")
        st.stop()

    st.success(f"Fetched {len(comments)} comments!")

    # ---------------------------------------------------------
    # SENTIMENT ANALYSIS
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

    st.subheader("🧾 Full Comment Dataset")
    st.dataframe(df, use_container_width=True)

    # ---------------------------------------------------------
    # VISUALIZATIONS
    # ---------------------------------------------------------
    st.subheader("📈 Visual Insights")
    col1, col2 = st.columns(2)

    # ---------- SENTIMENT BAR CHART ----------
    with col1:
        fig1, ax1 = plt.subplots()
        sentiment_counts = df["sentiment"].value_counts()
        colors = {"Positive": "green", "Neutral": "gray", "Negative": "red"}
        sentiment_counts.plot(
            kind="bar",
            color=[colors[s] for s in sentiment_counts.index],
            ax=ax1
        )
        ax1.set_title("Sentiment Distribution")
        ax1.set_xlabel("")
        ax1.set_ylabel("Count")
        ax1.tick_params(axis='x', rotation=0)
        st.pyplot(fig1)

    # ---------- POLARITY HISTOGRAM WITH RED→GREEN BAR COLORS ----------
    with col2:
        fig2, ax2 = plt.subplots()
        vals = df["polarity"].dropna().values
        bins = 20
        counts, bin_edges = np.histogram(vals, bins=bins, range=(-1, 1))

        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        norm_centers = (bin_centers + 1) / 2
        cmap = plt.get_cmap("RdYlGn")
        bar_colors = [cmap(n) for n in norm_centers]

        ax2.bar(
            bin_centers,
            counts,
            width=(bin_edges[1] - bin_edges[0]) * 0.95,
            color=bar_colors,
            edgecolor="black"
        )
        ax2.set_title("Polarity Distribution")
        ax2.set_xlabel("Polarity (-1 = Negative, +1 = Positive)")
        ax2.set_ylabel("Frequency")
        ax2.set_xlim(-1, 1)
        st.pyplot(fig2)

    # ---------------------------------------------------------
    # TOP 10 POSITIVE & NEGATIVE TABLES
    # ---------------------------------------------------------
    st.subheader("🏆 Top Comments")
    top_pos = df.sort_values(by="polarity", ascending=False).head(10)
    top_neg = df.sort_values(by="polarity", ascending=True).head(10)
    col3, col4 = st.columns(2)

    with col3:
        st.write("### 🌟 Top 10 Most Positive Comments")
        st.table(top_pos)

    with col4:
        st.write("### 💀 Top 10 Most Negative Comments")
        st.table(top_neg)

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

