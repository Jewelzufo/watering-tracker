# 🌱 Plant Watering Tracker

A simple Streamlit app to manage plants and visualize watering history with color-coded indicators.

- 🟢 Green: Watered within the last 3 days
- 🟡 Yellow: Watered 4-7 days ago
- 🔴 Red: Watered more than 7 days ago

Data is stored in `st.session_state` only. It resets when the app restarts or the session ends. No database required.

## Project structure

```
plant-watering-tracker/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── config.toml
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL shown in your terminal, usually http://localhost:8501

## Deploy to Streamlit Cloud via GitHub

1. Create a new public GitHub repo, for example `plant-watering-tracker`.
2. Upload all files in this folder to that repo. Keep `app.py` at the repo root.
3. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
4. Click **Create app** / **New app**.
5. Select your repo, branch `main`, and main file path `app.py`.
6. Click **Deploy**. Streamlit Cloud installs from `requirements.txt` automatically.

## Notes

- If you rename `app.py`, update the main file path in Streamlit Cloud to match.
- To change colors or thresholds, edit `get_status()` in `app.py`.
