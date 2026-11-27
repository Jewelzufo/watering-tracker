import streamlit as st
from datetime import datetime, date
import csv
import json
import io

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

def parse_datetime(value):
    """Parse ISO datetime or date string. Returns datetime or None."""
    if not value or str(value).strip() == "":
        return None
    value = str(value).strip()
    try:
        # Handles "2026-11-26T14:30:00" and "2026-11-26"
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        # Try common fallback formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None

# --- Export helpers ---
def build_csv(plants):
    """One row per watering. Plants with no history get one row with empty date."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["plant_name", "watering_datetime"])
    for p in plants:
        if not p["watering_dates"]:
            writer.writerow([p["plant_name"], ""])
        else:
            for dt in sorted(p["watering_dates"]):
                writer.writerow([p["plant_name"], dt.isoformat()])
    return output.getvalue()

def build_json(plants):
    """Same structure as session state, but with ISO strings for portability."""
    data = [
        {
            "plant_name": p["plant_name"],
            "watering_dates": [dt.isoformat() for dt in sorted(p["watering_dates"])],
        }
        for p in plants
    ]
    return json.dumps(data, indent=2)

def parse_imported_file(uploaded):
    """
    Returns (plants_list, error_message).
    Accepts .json (list of {plant_name, watering_dates}) or .csv (plant_name, watering_datetime).
    """
    try:
        raw = uploaded.getvalue().decode("utf-8")
    except Exception:
        return None, "Could not read file. Please upload a UTF-8 CSV or JSON file."

    # JSON path
    if uploaded.name.lower().endswith(".json"):
        try:
            data = json.loads(raw)
        except Exception:
            return None, "Invalid JSON file."
        # Allow either a list or {"plants": [...]}
        if isinstance(data, dict) and "plants" in data:
            data = data["plants"]
        if not isinstance(data, list):
            return None, "JSON must be a list of plants, or an object with a 'plants' list."
        parsed = []
        for item in data:
            if not isinstance(item, dict) or "plant_name" not in item:
                continue
            name = str(item["plant_name"]).strip()
            if not name:
                continue
            dates = []
            for v in item.get("watering_dates", []) or []:
                dt = parse_datetime(v)
                if dt:
                    dates.append(dt)
            parsed.append({"plant_name": name, "watering_dates": sorted(set(dates))})
        return parsed, None

    # CSV path
    if uploaded.name.lower().endswith(".csv"):
        try:
            reader = csv.DictReader(io.StringIO(raw))
            if not reader.fieldnames:
                return None, "CSV is empty."
            # Normalize headers: support watering_datetime, watering_date, date
            field_map = { (f or "").strip().lower(): f for f in reader.fieldnames }
            name_key = field_map.get("plant_name") or field_map.get("plant") or field_map.get("name")
            date_key = field_map.get("watering_datetime") or field_map.get("watering_date") or field_map.get("date") or field_map.get("watered_at")
            if not name_key:
                return None, "CSV must have a 'plant_name' column."
            grouped = {}
            for row in reader:
                name = str(row.get(name_key, "") or "").strip()
                if not name:
                    continue
                grouped.setdefault(name, [])
                if date_key:
                    dt = parse_datetime(row.get(date_key, ""))
                    if dt:
                        grouped[name].append(dt)
            parsed = [{"plant_name": n, "watering_dates": sorted(set(d))} for n, d in grouped.items()]
            return parsed, None
        except Exception:
            return None, "Could not parse CSV. Check headers: plant_name, watering_datetime"

    return None, "Please upload a .csv or .json file."

def merge_imported(imported):
    """Merge imported plants into session state, deduping watering dates."""
    added_plants = 0
    added_waterings = 0
    for imp in imported:
        # Find existing plant case-insensitively
        existing = next((p for p in st.session_state.plants if p["plant_name"].lower() == imp["plant_name"].lower()), None)
        if existing is None:
            st.session_state.plants.append({"plant_name": imp["plant_name"], "watering_dates": list(imp["watering_dates"])})
            added_plants += 1
            added_waterings += len(imp["watering_dates"])
        else:
            before = set(existing["watering_dates"])
            for dt in imp["watering_dates"]:
                if dt not in before:
                    existing["watering_dates"].append(dt)
                    before.add(dt)
                    added_waterings += 1
            existing["watering_dates"] = sorted(existing["watering_dates"])
    return added_plants, added_waterings

# --- Session state: single source of truth for plants ---
# Structure: [{"plant_name": str, "watering_dates": [datetime, ...]}, ...]
if "plants" not in st.session_state:
    st.session_state.plants = []
if "import_preview" not in st.session_state:
    st.session_state.import_preview = None

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

# --- Import / Export History ---
with st.expander("📥📤 Import / Export History", expanded=False):
    st.markdown("Backup your history to CSV or JSON, or restore it on another device. Import merges with existing plants and skips duplicate dates.")

    # Export
    st.markdown("**Export**")
    e_csv, e_json = st.columns(2)
    with e_csv:
        st.download_button(
            "Download CSV",
            data=build_csv(st.session_state.plants),
            file_name=f"plant-watering-{date.today().isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=not st.session_state.plants,
        )
    with e_json:
        st.download_button(
            "Download JSON",
            data=build_json(st.session_state.plants),
            file_name=f"plant-watering-{date.today().isoformat()}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not st.session_state.plants,
        )
    if not st.session_state.plants:
        st.caption("Add a plant first to enable export.")

    st.divider()

    # Import
    st.markdown("**Import**")
    st.caption("Accepted: CSV with `plant_name, watering_datetime` or JSON in the same format as export.")
    uploaded = st.file_uploader("Choose a CSV or JSON file", type=["csv", "json"], key="history_uploader")

    if uploaded is not None:
        # Parse only when a new file is uploaded, cache in session state for preview
        if st.session_state.get("last_upload_name") != uploaded.name:
            parsed, err = parse_imported_file(uploaded)
            st.session_state.import_preview = parsed
            st.session_state.import_error = err
            st.session_state.last_upload_name = uploaded.name

        if st.session_state.get("import_error"):
            st.error(st.session_state.import_error)
        elif st.session_state.import_preview is not None:
            preview = st.session_state.import_preview
            total_import_dates = sum(len(p["watering_dates"]) for p in preview)
            st.info(f"Preview: {len(preview)} plant(s), {total_import_dates} watering(s) found.")
            for p in preview:
                last = f" • last: {max(p['watering_dates']).strftime('%b %d, %Y')}" if p["watering_dates"] else " • no dates"
                st.caption(f"• {p['plant_name']} — {len(p['watering_dates'])} watering(s){last}")

            c_import, c_clear = st.columns(2)
            with c_import:
                if st.button("Import & Merge", type="primary", use_container_width=True):
                    added_plants, added_waterings = merge_imported(preview)
                    st.session_state.import_preview = None
                    st.session_state.last_upload_name = None
                    st.success(f"Imported! {added_plants} new plant(s), {added_waterings} new watering(s) added. Duplicates skipped.")
                    st.rerun()
            with c_clear:
                if st.button("Cancel Import", use_container_width=True):
                    st.session_state.import_preview = None
                    st.session_state.last_upload_name = None
                    st.rerun()

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
st.caption("Data is stored in session state only. Use Import / Export to back it up, since it resets when the app restarts.")
