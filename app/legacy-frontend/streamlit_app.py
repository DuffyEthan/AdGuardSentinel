import streamlit as st
import psycopg
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date


st.set_page_config(page_title="Project Name", layout="wide")

# CSS
RUBY = "#8B0000"        
RUBY_GLOW = "#B30000"   
MATTE_BLACK = "#0b0b0d" 

st.markdown(
    f"""
    <style>
      /* App background (matte black) */
      .stApp {{
        background: {MATTE_BLACK};
        color: #f2f2f2;
      }}

      /* Diagonal ruby slash */
      .stApp::before {{
        content: "";
        position: fixed;
        top: -25vh;
        right: -35vw;
        width: 80vw;
        height: 160vh;
        background: linear-gradient(
          120deg,
          transparent 35%,
          {RUBY} 35%,
          {RUBY} 60%,
          transparent 60%
        );
        opacity: 0.35;
        transform: rotate(-8deg);
        pointer-events: none;
        z-index: 0;
      }}

      /* Keep content above the slash */
      .block-container {{
        position: relative;
        z-index: 1;
        padding-top: 3rem;
      }}

      /* Title text */
      .project-title {{
        font-size: 3rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
      }}

      .subtitle {{
        color: #cfcfcf;
        margin-bottom: 2rem;
      }}

      /* Panels/cards */
      .panel {{
        background: rgba(20, 20, 24, 0.70);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 18px;
        padding: 1.25rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
      }}

      /* Streamlit buttons */
      div.stButton > button {{
        width: 100%;
        border-radius: 14px;
        padding: 0.9rem 1.1rem;
        font-size: 1.05rem;
        font-weight: 700;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(139, 0, 0, 0.20);
        color: #fff;
        transition: all 160ms ease-in-out;
      }}

      div.stButton > button:hover {{
        border-color: {RUBY_GLOW};
        background: rgba(179, 0, 0, 0.35);
        box-shadow: 0 0 0 4px rgba(179,0,0,0.18);
        transform: translateY(-1px);
      }}

      /* Date input styling */
      .stDateInput > div > div {{
        background: rgba(20, 20, 24, 0.70) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
      }}

      /* Dataframe container */
      [data-testid="stDataFrame"] {{
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
      }}

      header[data-testid="stHeader"] {{
        background: transparent;
      }}

      a {{
        color: {RUBY_GLOW} !important;
      }}

      /* Sidebar styling */
      [data-testid="stSidebar"] {{
        background: rgba(15, 15, 18, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
      }}

      [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        padding-top: 1rem;
      }}

      /* Scrollable sidebar content */
      [data-testid="stSidebarContent"] {{
        overflow-y: auto;
        max-height: 100vh;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# What page of wesite are we on
if "page" not in st.session_state:
    st.session_state.page = "home"

def go(page_name: str) -> None:
    st.session_state.page = page_name
    st.rerun()


# Allows us to connect to the database
def get_conn():
    return psycopg.connect(
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
    )

# Prevents reloading data on every interaction (unused - kept for future DB integration)
@st.cache_data(ttl=30)
def load_day(selected_day: date) -> pd.DataFrame:
    sql = """
        SELECT impression_time, impression_clicks
        FROM impression
        WHERE impression_date = %s
    """
    with get_conn() as conn:
        return pd.read_sql(sql, conn, params=(selected_day,))

# Builds the hourly dataframe (unused - kept for future DB integration)
def build_hourly(df_raw: pd.DataFrame) -> pd.DataFrame:
    df_raw = df_raw.copy()
    df_raw["impression_time"] = pd.to_datetime(df_raw["impression_time"].astype(str)).dt.time
    df_raw["hour"] = df_raw["impression_time"].apply(lambda t: t.hour)

    hourly = (
        df_raw.groupby("hour", as_index=False)["impression_clicks"]
        .sum()
        .rename(columns={"impression_clicks": "clicks"})
    )

    all_hours = pd.DataFrame({"hour": list(range(24))})
    hourly = all_hours.merge(hourly, on="hour", how="left").fillna({"clicks": 0})
    hourly["clicks"] = hourly["clicks"].astype(int)
    return hourly

# Publisher definitions
PUBLISHERS = ["SPY", "CAT", "DOG", "OWL", "FOX"]

# Initialize synthetic time-series data: f(x) = 2 + sin(10x) for a given publisher
def generate_publisher_data(publisher: str) -> pd.DataFrame:
    seed = sum(ord(c) for c in publisher)
    np.random.seed(seed)
    x = np.linspace(0, 100, 100)
    y = 2 + np.sin(10 * x)
    return pd.DataFrame({"x": x, "y": y})

# Designs the stock market style plot (unused - kept for future DB integration)
def plot_stockmarket_style(hourly: pd.DataFrame, selected_day: date):
    fig, ax = plt.subplots(figsize=(13, 4.5))


    fig.patch.set_alpha(0)
    ax.set_facecolor("none")


    RUBY = "#8B0000"
    RUBY_LINE = "#B30000"
    TEXT = "#E6E6E6"
    GRID = "#666666"




    ax.plot(
        hourly["hour"],
        hourly["clicks"],
        color=RUBY_LINE,
        linewidth=2.8,
        marker="o",
        markersize=5,
        zorder=3
    )


    ax.set_title(
        f"Hourly Impression Volume — {selected_day.isoformat()}",
        fontsize=15,
        fontweight="bold",
        color=TEXT,
        pad=14
    )

    ax.set_xlabel("Hour (24h)", fontsize=12, color=TEXT, labelpad=10)
    ax.set_ylabel("Clicks", fontsize=12, color=TEXT, labelpad=10)


    ax.set_xticks(range(24))
    ax.tick_params(axis="x", colors=TEXT, labelsize=10)
    ax.tick_params(axis="y", colors=TEXT, labelsize=10)

    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(0, 20)
    ax.set_yticks(range(0, 21, 1))



    ax.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.7,
        alpha=0.35,
        color=GRID,
        zorder=1
    )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.spines["left"].set_color(TEXT)
    ax.spines["bottom"].set_color(TEXT)

    return fig

# Plot synthetic time-series data for a publisher
def plot_publisher_timeseries(df: pd.DataFrame, publisher: str):
    fig, ax = plt.subplots(figsize=(13, 4.5))

    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    RUBY_LINE = "#B30000"
    TEXT = "#E6E6E6"
    GRID = "#666666"

    ax.plot(
        df["x"],
        df["y"],
        color=RUBY_LINE,
        linewidth=2.8,
        zorder=3
    )

    ax.set_title(
        f"{publisher} — Time Series: f(x) = 2 + sin(10x)",
        fontsize=15,
        fontweight="bold",
        color=TEXT,
        pad=14
    )

    ax.set_xlabel("x", fontsize=12, color=TEXT, labelpad=10)
    ax.set_ylabel("y", fontsize=12, color=TEXT, labelpad=10)

    ax.tick_params(axis="x", colors=TEXT, labelsize=10)
    ax.tick_params(axis="y", colors=TEXT, labelsize=10)

    ax.set_ylim(0, 4)

    ax.grid(
        True,
        axis="y",
        linestyle="--",
        linewidth=0.7,
        alpha=0.35,
        color=GRID,
        zorder=1
    )

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    ax.spines["left"].set_color(TEXT)
    ax.spines["bottom"].set_color(TEXT)

    return fig

# Pages
def render_home():
    col1, col2 = st.columns([1.2, 0.9], gap="large")

    with col1:
        st.markdown('<div class="project-title">Project Name</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Select an advert to view performance charts.</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.write("Welcome. This is your dashboard homepage.")
        st.write("Click **Advert A** to open the calendar view data.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Dashboards")

        if st.button("Advert A", use_container_width=True):
            go("advert_a")

        st.caption("Add more advert buttons here later.")
        st.markdown("</div>", unsafe_allow_html=True)

def render_advert_a():
    # Initialize selected publisher in session state
    if "selected_publisher" not in st.session_state:
        st.session_state.selected_publisher = PUBLISHERS[0]

    # Sidebar for publisher selection
    with st.sidebar:
        st.markdown('<div class="project-title" style="font-size: 1.5rem;">Publishers</div>', unsafe_allow_html=True)
        st.markdown("---")

        for pub in PUBLISHERS:
            is_selected = st.session_state.selected_publisher == pub
            if st.button(
                f"{'> ' if is_selected else ''}{pub}",
                key=f"pub_{pub}",
                use_container_width=True
            ):
                st.session_state.selected_publisher = pub
                st.rerun()

    # Main content
    selected = st.session_state.selected_publisher

    top = st.columns([1, 0.35], vertical_alignment="center")

    with top[0]:
        st.markdown(f'<div class="project-title">{selected}</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Synthetic time-series data: f(x) = 2 + sin(10x)</div>', unsafe_allow_html=True)

    with top[1]:
        if st.button("← Back to Home", use_container_width=True):
            go("home")

    st.markdown('<div class="panel">', unsafe_allow_html=True)

    df_publisher = generate_publisher_data(selected)
    fig = plot_publisher_timeseries(df_publisher, selected)

    st.pyplot(fig, clear_figure=True)

    with st.expander("Show time-series data"):
        st.dataframe(df_publisher, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# Routes to correct page
if st.session_state.page == "home":
    render_home()
elif st.session_state.page == "advert_a":
    render_advert_a()
else:
    st.session_state.page = "home"
    st.rerun()


