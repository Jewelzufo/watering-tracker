import streamlit as st
from datetime import datetime, date

# --- Page config: centered layout works well on mobile ---
st.set_page_config(page_title="Plant Watering Tracker", page_icon="🌱", layout="centered")

# --- Helper: color logic based on recency ---
def get_status(days_ago):
    """Return (hex_color, label, emoji) for days since watering."""
    if days_ago <= 3:
        return "#22c55e", "Watered recently", "🟢"
    if days_ago <= 7:
        return "#eab308", "Due soon", "🟡"
    return "#ef4444", "Needs water", "🔴"

def days_since(watering_dt):
    """Days between now and a watering datetime."""
    return (datetime.now() - watering_dt).days

# --- Session state: single source of truth for plants ---
# Structure: [{"plant_name": str, "watering_dates": [datetime, ...]}, ...]
if "plants" not in st.session_state:
    st.session_state.plants = []

st.title("🌱 Plant Watering Tracker")
st.caption("Log waterings and see at a glance which plants need attention.")

# --- Summary metrics ---
total = len(st.session_state.plants)
needs_water = 0
for p in st.session_state.plants:
    if not p["watering_dates"]:
        needs_water += 1
    elif days_since(max(p["watering_dates"])) > 7:
        needs_water += 1

col1, col2, col3 = st.columns(3)
col1.metric("Plants", total)
col2.metric("Needs water", needs_water)
col3.metric("Recently watered", total - needs_water if total else 0)

# --- Add Plant Section ---
st.header("Add Plant")
with st.container(border=True):
    new_name = st.text_input("Plant name", placeholder="e.g. Monstera", key="new_plant_name")
    if st.button("Add Plant", type="primary", use_container_width=True):
        cleaned = new_name.strip() if new_name else ""
        if not cleaned:
            st.warning("Please enter a plant name before adding.")
        elif any(p["plant_name"].lower() == cleaned.lower() for p in st.session_state.plants):
            st.warning(f"'{cleaned}' is already in your list.")
        else:
            # New plant starts with an empty watering history
            st.session_state.plants.append({"plant_name": cleaned, "watering_dates": []})
            st.success(f"Added {cleaned}!")
            st.rerun()

# --- Plant List & History Section ---
st.header("Your Plants")

if not st.session_state.plants:
    st.info("No plants yet. Add one above to start tracking.")
else:
    # Show most recently watered first, never-watered at the end
    sorted_plants = sorted(
        enumerate(st.session_state.plants),
        key=lambda x: max(x[1]["watering_dates"]) if x[1]["watering_dates"] else datetime.min,
        reverse=True,
    )
    for orig_idx, plant in sorted_plants:
        dates = sorted(plant["watering_dates"], reverse=True)

        # Overall plant status from most recent watering
        if not dates:
            status_color, status_label, status_emoji = "#94a3b8", "Never watered", "⚪"
            status_text = "No waterings logged yet"
        else:
            d = days_since(dates[0])
            status_color, status_label, status_emoji = get_status(d)
            status_text = f"Last watered {d} day(s) ago • {dates[0].strftime('%b %d, %Y at %I:%M %p')}"

        with st.container(border=True):
            st.subheader(f"{status_emoji} {plant['plant_name']}")
            # Color-coded status indicator
            st.markdown(
                f"<span style='background-color:{status_color}; color:white; padding:4px 10px; border-radius:20px; font-size:0.85em; font-weight:600;'>{status_label}</span> &nbsp; {status_text}",
                unsafe_allow_html=True,
            )

            # Log watering: defaults to today, allows backfill via date picker
            c_date, c_btn = st.columns([1, 1])
            with c_date:
                log_date = st.date_input(
                    "Watering date",
                    value=date.today(),
                    key=f"date_{orig_idx}",
                    label_visibility="collapsed",
                )
            with c_btn:
                if st.button("💧 Log Watering", key=f"log_{orig_idx}", use_container_width=True):
                    # Combine selected date with current time so ordering stays correct
                    log_dt = datetime.combine(log_date, datetime.now().time())
                    st.session_state.plants[orig_idx]["watering_dates"].append(log_dt)
                    st.success(f"Logged watering for {plant['plant_name']} on {log_dt.strftime('%b %d, %Y')}")
                    st.rerun()

            # Watering history with per-date color coding
            if dates:
                st.markdown("**Watering History**")
                for dt in dates:
                    ago = days_since(dt)
                    color, label, emoji = get_status(ago)
                    st.markdown(
                        f"<div style='display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid #f1f5f9;'>"
                        f"<span style='width:12px; height:12px; border-radius:50%; background:{color}; display:inline-block;'></span>"
                        f"<span style='color:{color}; font-weight:600;'>{dt.strftime('%b %d, %Y at %I:%M %p')}</span>"
                        f"<span style='color:#64748b; font-size:0.9em;'>• {ago} day(s) ago • {label}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No watering history yet.")

            # Danger zone: remove plant
            if st.button("Remove plant", key=f"delete_{orig_idx}"):
                removed = st.session_state.plants.pop(orig_idx)
                st.warning(f"Removed {removed['plant_name']}")
                st.rerun()

# --- Legend ---
st.divider()
st.markdown("**Legend:** 🟢 Watered within last 3 days &nbsp; 🟡 Watered 4-7 days ago &nbsp; 🔴 Watered more than 7 days ago")
st.caption("Data is stored in session state only and resets when the app restarts.")
