import streamlit as st
import pandas as pd
import numpy as np
import requests
from textblob import TextBlob
import matplotlib.pyplot as plt

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
    import re
    match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if not match:
        st.error("Invalid YouTube URL format.")
        st.stop()
    video_id = match.group(1)

    # ---------------------------------------------------------
    # FETCH COMMENTS
    # ---------------------------------------------------------
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText"
    }

    response = requests.get(url, params=params)
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

        # Label sentiment
        if polarity > 0.05:
            sentiment_labels.append("Positive")
        elif polarity < -0.05:
            sentiment_labels.append("Negative")
        else:
            sentiment_labels.append("Neutral")

    # Create DataFrame
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
    st.subheader("📈 Visual Insights")
    col1, col2 = st.columns(2)

    # ---------- LEFT: SENTIMENT BAR CHART ----------
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

    # ---------- RIGHT: POLARITY HISTOGRAM ----------
    with col2:
        fig2, ax2 = plt.subplots()

        vals = df["polarity"].dropna().values
        bins = 20
        counts, bin_edges = np.histogram(vals, bins=bins, range=(-1, 1))

        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        norm_centers = (bin_centers + 1) / 2  # map -1..1 → 0..1

        cmap = plt.get_cmap("RdYlGn")  # red → yellow → green
        bar_colors = [cmap(n) for n in norm_centers]

        ax2.bar(
            bin_centers,
            counts,
            width=(bin_edges[1] - bin_edges[0]) * 0.95,
            color=bar_colors,
            edgecolor="black"
        )

        ax2.set_title("Polarity Distribution (Red → Green)")
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

    cola, colb = st.columns(2)

    with cola:
        st.write("### 🌟 Top 10 Most Positive Comments")
        st.table(top_pos)

    with colb:
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
