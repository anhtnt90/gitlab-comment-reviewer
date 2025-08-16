# GitLab MR Comments Viewer

This application is a Streamlit-based web UI for viewing and exporting comments from GitLab Merge Requests (MRs) with the label `NashTech`. It allows you to filter by MR IDs, group comments by MR and code line, and export results to Markdown or CSV.

## Features
- Enter GitLab URL, Project ID, and Private Token
- Optionally filter by a list of MR IDs
- View comments grouped by MR and code line
- Syntax highlighting for code snippets
- Export results to Markdown and CSV
- (Optional) Hide Streamlit menu items using a CSS/JS workaround

## Prerequisites
- Python 3.8+
- GitLab account and a valid Private Token with API access
- The following Python packages:
  - streamlit
  - requests
  - pandas

## Installation
1. Clone or download this repository.
2. Open a terminal in the project directory.
3. (Recommended) Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```powershell
   pip install streamlit requests pandas
   ```

## Running the Application
1. Start the Streamlit app:
   ```powershell
   streamlit run app.py
   ```
   Or, if using the virtual environment directly:
   ```powershell
   .venv\Scripts\python.exe -m streamlit run app.py
   ```
2. Open your browser and go to [http://localhost:8501](http://localhost:8501)

## Usage
1. Fill in your GitLab URL, Project ID, and Private Token in the configuration section.
2. Optionally, enter a comma-separated list of MR IDs to filter specific merge requests.
3. Click **Run Analysis** to fetch and display comments.
4. View results grouped by MR and code line in the UI.
5. Use the **Export Markdown** and **Export CSV** buttons to download results.

## Notes
- The three-dot menu in the top right is part of Streamlit's default UI. You can attempt to hide menu items using the provided workaround in `app.py`, but this is not officially supported.
- The screencast feature in the menu records your browser session and saves the video to your Downloads folder.
- For best results, use a GitLab Private Token with `api` scope.

## Troubleshooting
- If you see `No module named streamlit`, make sure you installed dependencies in the correct environment.
- If you have issues with API access, check your token permissions and project ID.
- For UI issues, try updating Streamlit to the latest version:
   ```powershell
   pip install --upgrade streamlit
   ```

## License
MIT
