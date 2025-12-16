import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi
import re

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="YouTube Caption Sentiment Timeline",
    layout="wide"
)

st.title("🎬 YouTube Caption Sentiment Analyzer")
st.write("Sentiment analysis using **ONLY YouTube captions** (no comments, no API key).")

# ----------------------------
# INPUT
# ----------------------------
video_url = st.text_input("🔗 Enter YouTube Video URL")

# ----------------------------
# TRANSCRIPT FETCH LOGIC
# ----------------------------
def fetch_transcript(video_id):
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # 1️⃣ Manual English
    try:
        return transcript_list.find_manually_created_transcript(['en']).fetch()
    except:
        pass

    # 2️⃣ Auto-generated English
    try:
        return transcript_list.find_generated_transcript(['en']).fetch()
    except:
        pass

    # 3️⃣ Any language → translate to English
    for transcript in transcript_list:
        try:
            return transcript.translate('en').fetch()
        except:
            continue

    raise RuntimeError("Captions exist but could not be accessed.")

# ----------------------------
# MAIN ACTION
# ----------------------------
if st.button("Analyze Captions"):

    if not video_url:
        st.error("Please enter a YouTube video URL.")
        st.stop()

    # Extract video ID
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", video_url)
    if not match:
        st.error("Invalid YouTube URL.")
        st.stop()

    video_id = match.group(1)

    # ----------------------------
    # FETCH CAPTIONS
    # ----------------------------
    try:
        transcript = fetch_transcript(video_id)
    except Exception:
        st.error("Captions are not accessible for this video.")
        st.stop()

    # ----------------------------
    # BUILD DATAFRAME
    # ----------------------------
    df = pd.DataFrame(transcript)
    df = df[["start", "duration", "text"]]
    df["time_min"] = df["start"] / 60

    # ----------------------------
    # SENTIMENT ANALYSIS
    # ----------------------------
    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)

    def label_sentiment(p):
        if p > 0.05:
            return "Positive"
        elif p < -0.05:
            return "Negative"
        else:
            return "Neutral"

    df["sentiment"] = df["polarity"].apply(label_sentiment)

    # Smoothed polarity
    df["rolling_polarity"] = df["polarity"].rolling(
        window=10, min_periods=1
    ).mean()

    # ----------------------------
    # PREVIEW
    # ----------------------------
    st.subheader("📝 Caption Preview")
    st.dataframe(df.head(30), use_container_width=True)

    # ----------------------------
    # VISUALS
    # ----------------------------
    st.subheader("📈 Sentiment Over Time")

    col1, col2 = st.columns(2)

    # Polarity timeline
    with col1:
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(df["time_min"], df["polarity"], alpha=0.4)
        ax1.plot(df["time_min"], df["rolling_polarity"], linewidth=2)
        ax1.axhline(0, linestyle="--")

        ax1.set_title("Sentiment Polarity Timeline")
        ax1.set_xlabel("Time (minutes)")
        ax1.set_ylabel("Polarity")
        st.pyplot(fig1)

    # Sentiment distribution
    with col2:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        df["sentiment"].value_counts().plot(kind="bar", ax=ax2)
        ax2.set_title("Caption Sentiment Distribution")
        ax2.set_ylabel("Count")
        st.pyplot(fig2)

    # ----------------------------
    # POLARITY HISTOGRAM
    # ----------------------------
    st.subheader("📊 Polarity Distribution")

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.hist(df["polarity"], bins=30)
    ax3.set_title("Histogram of Caption Polarity")
    ax3.set_xlabel("Polarity")
    ax3.set_ylabel("Frequency")
    st.pyplot(fig3)

    # ----------------------------
    # STRONGEST MOMENTS
    # ----------------------------
    st.subheader("🔥 Strongest Emotional Moments")

    colA, colB = st.columns(2)

    with colA:
        st.write("### 🌟 Most Positive Captions")
        st.table(
            df.sort_values("polarity", ascending=False)
              .head(10)[["time_min", "polarity", "text"]]
              .reset_index(drop=True)
        )

    with colB:
        st.write("### 💀 Most Negative Captions")
        st.table(
            df.sort_values("polarity")
              .head(10)[["time_min", "polarity", "text"]]
              .reset_index(drop=True)
        )

    # ----------------------------
    # DOWNLOAD
    # ----------------------------
    st.subheader("⬇️ Download Results")

    st.download_button(
        label="Download Caption Sentiment CSV",
        data=df.to_csv(index=False).encode(),
        file_name="caption_sentiment_timeline.csv",
        mime="text/csv"
    )
