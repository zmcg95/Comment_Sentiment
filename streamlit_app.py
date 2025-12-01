import streamlit as st
import pandas as pd
import numpy as np
import requests
from textblob import TextBlob
import matplotlib.pyplot as plt
import re

# ------------------------------------------------------
# PAGE SETTINGS
# ------------------------------------------------------
st.set_page_config(page_title="YouTube Channel Analyzer", layout="wide")
st.title("📊 YouTube Channel & Video Sentiment Analyzer")

# ------------------------------------------------------
# USER INPUT
# ------------------------------------------------------
api_key = st.text_input("🔑 Enter YouTube API Key", type="password")
channel_url = st.text_input("📺 Enter YouTube Channel URL")

# Extract channel ID from URL
def extract_channel_id(url):
    """
    Supports:
    - https://www.youtube.com/channel/CHANNEL_ID
    - https://www.youtube.com/@username  (converted into channel ID)
    """
    # Direct channel link
    match = re.search(r"channel/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    # Handle @username to channel ID lookup
    username_match = re.search(r"youtube.com/@([a-zA-Z0-9_]+)", url)
    if username_match:
        username = username_match.group(1)
        # Convert @username --> channel ID
        lookup_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": username,
            "type": "channel",
            "key": api_key,
            "maxResults": 1
        }
        res = requests.get(lookup_url, params=params).json()
        try:
            return res["items"][0]["snippet"]["channelId"]
        except:
            return None

    return None


# ------------------------------------------------------
# LOAD CHANNEL INFO
# ------------------------------------------------------
if st.button("Load Channel"):
    if not api_key or not channel_url:
        st.error("Please enter API key AND channel URL.")
        st.stop()

    channel_id = extract_channel_id(channel_url)

    if not channel_id:
        st.error("Could not extract channel ID.")
        st.stop()

    # Fetch channel metadata
    ch_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,statistics",
        "id": channel_id,
        "key": api_key
    }
    ch_resp = requests.get(ch_url, params=params).json()

    try:
        snippet = ch_resp["items"][0]["snippet"]
        stats = ch_resp["items"][0]["statistics"]
    except:
        st.error("Failed to load channel data.")
        st.stop()

    title = snippet["title"]
    thumbnail = snippet["thumbnails"]["high"]["url"]
    subs = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    total_videos = int(stats.get("videoCount", 0))

    # ------------------------------------------------------
    # DISPLAY CHANNEL KPIs
    # ------------------------------------------------------
    st.subheader(f"📺 Channel Overview: **{title}**")

    colA, colB = st.columns([1, 3])

    with colA:
        st.image(thumbnail, width=250)

    with colB:
        m1, m2, m3 = st.columns(3)
        m1.metric("👥 Subscribers", f"{subs:,}")
        m2.metric("👁️ Total Views", f"{total_views:,}")
        m3.metric("🎞️ Total Videos", f"{total_videos:,}")

    # ------------------------------------------------------
    # FETCH LAST 50 VIDEOS
    # ------------------------------------------------------
    st.subheader("🎬 Recent Videos")

    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "maxResults": 50,
        "type": "video",
        "key": api_key
    }

    vid_resp = requests.get(search_url, params=params).json()
    videos = vid_resp.get("items", [])

    # ------------------------------------------------------
    # HORIZONTAL SCROLLING VIDEO STRIP
    # ------------------------------------------------------
    st.markdown("""
        <style>
        .scroll-row {
            display: flex;
            overflow-x: auto;
            padding: 10px;
            gap: 20px;
        }
        .video-card {
            min-width: 240px;
            max-width: 240px;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 8px;
            background: #fafafa;
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)

    st.write("### 👉 Select a video to analyze")

    # Scroll container
    st.markdown('<div class="scroll-row">', unsafe_allow_html=True)

    selected_video = None

    for v in videos:
        vid = v["id"]["videoId"]
        thumb = v["snippet"]["thumbnails"]["high"]["url"]
        title_vid = v["snippet"]["title"]

        card_html = f"""
            <div class="video-card">
                <img src="{thumb}" width="220">
                <p><b>{title_vid[:50]}...</b></p>
                <form action="" method="get">
                    <button name="video_to_analyze" value="{vid}">Analyze</button>
                </form>
            </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ------------------------------------------------------
    # HANDLE VIDEO SELECTION
    # ------------------------------------------------------
    video_to_analyze = st.query_params.get("video_to_analyze", None)

    if video_to_analyze:
        st.subheader("📊 Video Selected for Analysis")
        st.write(f"Video ID: **{video_to_analyze}**")

        # Fetch video metadata
        video_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics",
            "id": video_to_analyze,
            "key": api_key
        }
        vresp = requests.get(video_url, params=params).json()

        try:
            vsnip = vresp["items"][0]["snippet"]
            vstats = vresp["items"][0]["statistics"]
        except:
            st.error("Error loading video details.")
            st.stop()

        vtitle = vsnip["title"]
        vthumb = f"https://img.youtube.com/vi/{video_to_analyze}/maxresdefault.jpg"
        vviews = int(vstats.get("viewCount", 0))
        vlikes = int(vstats.get("likeCount", 0))
        vcomments = int(vstats.get("commentCount", 0))

        eng_rate = ((vlikes + vcomments) / max(vviews, 1)) * 100

        # Display video section
        colv1, colv2 = st.columns([1, 2])

        with colv1:
            st.image(vthumb, width=350)

        with colv2:
            st.write(f"### {vtitle}")
            k1, k2, k3 = st.columns(3)
            k1.metric("👁️ Views", f"{vviews:,}")
            k2.metric("👍 Likes", f"{vlikes:,}")
            k3.metric("💬 Comments", f"{vcomments:,}")

            k4, k5 = st.columns(2)
            k4.metric("📈 Engagement Rate", f"{eng_rate:.2f}%")
            k5.metric("🔥 Custom Score", round(eng_rate * 0.5 + vlikes * 0.003, 2))

        # ------------------------------------------------------
        # FETCH VIDEO COMMENTS
        # ------------------------------------------------------
        comment_url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            "part": "snippet",
            "videoId": video_to_analyze,
            "key": api_key,
            "maxResults": 100,
            "textFormat": "plainText"
        }

        response = requests.get(comment_url, params=params).json()
        comments = [
            item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            for item in response.get("items", [])
        ]

        st.success(f"Fetched {len(comments)} comments.")

        # ------------------------------------------------------
        # SENTIMENT ANALYSIS
        # ------------------------------------------------------
        polarity = [TextBlob(c).sentiment.polarity for c in comments]
        sentiment = [
            "Positive" if p > 0.05 else "Negative" if p < -0.05 else "Neutral"
            for p in polarity
        ]

        df = pd.DataFrame({
            "comment": comments,
            "polarity": polarity,
            "sentiment": sentiment
        })

        st.subheader("🧾 Comments Dataset")
        st.dataframe(df)

        # ------------------------------------------------------
        # VISUALS
        # ------------------------------------------------------
        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots()
            df["sentiment"].value_counts().plot(
                kind="bar",
                color=["green", "gray", "red"],
                ax=ax
            )
            ax.set_title("Sentiment Distribution")
            st.pyplot(fig)

        with col2:
            fig, ax = plt.subplots()
            vals = df["polarity"].values
            counts, edges = np.histogram(vals, bins=20, range=(-1, 1))
            centers = (edges[:-1] + edges[1:]) / 2

            cmap = plt.get_cmap("RdYlGn")
            colors = [cmap((c + 1) / 2) for c in centers]

            ax.bar(centers, counts, width=0.09, color=colors, edgecolor="black")
            ax.set_title("Polarity Distribution")
            st.pyplot(fig)

        # Download CSV
        st.download_button(
            "⬇️ Download CSV",
            df.to_csv(index=False).encode(),
            file_name="comments_sentiment.csv",
            mime="text/csv"
        )
