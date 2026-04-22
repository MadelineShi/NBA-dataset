# HoopBase — NBA Shot Analytics Dashboard
**CSC 353 · Database Systems · Davidson College · Spring 2026**

Built entirely from per-game shot log CSVs (2000–present).
All stats (FG%, points, 3P%) are computed live from the shots table — no separate stats dataset needed.

---

## Project Structure

```
hoopbase/
├── schema.sql          ← run first in MySQL
├── load_data.py        ← loads all game CSVs into MySQL
├── app.py              ← Flask server
├── build_team_stats    ← Loads in team stats
├── build_stats         ← Loads in player stats
├── data/               ← put ALL your game CSV files here
│   ├── 20220313.csv
│   ├── 20220314.csv
│   └── ... (4000+ files)
└── templates/
    ├── base.html
    ├── home.html
    ├── search.html
    ├── player.html       ← includes interactive shot chart
    ├── compare.html
    ├── teams.html
    ├── team.html
    └── leaderboards.html
```

---

## Setup

### 1. Install Python dependencies
```
pip install flask mysql-connector-python pandas
```

### 2. Create the database
Open MySQL Workbench, open `schema.sql`, and click the ⚡ Run button.

### 3. Update your password
In both `load_data.py` and `app.py`, find:
```python
"password": "yourpassword",
```
Replace with your actual MySQL password.

### 4. NBA Dataset

## Data
The dataset is hosted on Kaggle. Download it here:
[NBA Dataset on Kaggle]: https://www.kaggle.com/datasets/techbaron13/nba-shots-dataset-2001-present
Once downloaded, place the folder in the root of the project as `/data`. Please make sure to make this folder. 

### 5. Load the data
```
python load_data.py
python build_team_stats.py
python build_stats.py
```
This will take several minutes for 4000+ files (~5-6 million shot rows total). It prints progress every 100 files so you can see it working. Safe to re-run — it skips already-loaded games.
The other two will load in player data and team data and will print progress accordingly for player every 100 files and team every single file. 

### 6. Run the site
```
python app.py
```
Open http://localhost:5000

---

## Features

| Route | Feature |
|---|---|
| `/` | Home — top scorers latest season |
| `/search` | Filter by name, team, season; sort any column |
| `/player/<name>` | Career log + **interactive shot chart** (green = made, red = missed) |
| `/compare?p1=&p2=` | Side-by-side career stat comparison |
| `/teams` | All teams ranked by total points |
| `/team/<abbrev>` | Season history + top players per year |
| `/leaderboards` | Total Pts, FG%, 3P%, most shots |
| `/api/shots/<name>` | JSON endpoint powering the shot chart |

---

