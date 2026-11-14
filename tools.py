import os
import subprocess
import pandas as pd

def setup_runtime(package: str) -> str:
    """Installs SDKs and developer runtimes on Windows silently via winget."""
    catalog = {
        "java": "Oracle.JDK.21",
        "jdk": "Oracle.JDK.21",
        "python": "Python.Python.3.12",
        "node": "OpenJS.NodeJS",
        "nodejs": "OpenJS.NodeJS",
        "git": "Git.Git",
        "vscode": "Microsoft.VisualStudioCode",
        "docker": "Docker.DockerDesktop",
        "rust": "Rustlang.Rustup",
        "go": "GoLang.Go"
    }
    pkg_id = catalog.get(package.lower().strip(), package)
    cmd = f'winget install --id {pkg_id} --exact --accept-package-agreements --accept-source-agreements --silent'
    
    print(f"\n[Peirro Ops] Executing installation for {pkg_id}...")
    try:
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=300)
        if res.returncode == 0:
            return f"Successfully installed and configured {package} ({pkg_id})."
        return f"Installer returned status code {res.returncode}:\n{res.stdout or res.stderr}"
    except Exception as e:
        return f"Setup error: {str(e)}"

def analyze_and_clean_dataset(file_path: str) -> str:
    """Cleans missing data, removes duplicates, and generates insights for CSV/Excel."""
    clean_path = file_path.strip().strip('"').strip("'")
    if not os.path.exists(clean_path):
        return f"File not found: {clean_path}"

    try:
        if clean_path.endswith('.csv'):
            df = pd.read_csv(clean_path)
        elif clean_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(clean_path)
        else:
            return "Unsupported format. Please provide a .csv or .xlsx file."

        init_len = len(df)
        df = df.drop_duplicates()
        dupes_removed = init_len - len(df)

        null_summary = df.isnull().sum().to_dict()
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(df[col].median())
            else:
                df[col] = df[col].fillna("Unknown")

        out_path = os.path.splitext(clean_path)[0] + "_cleaned.csv"
        df.to_csv(out_path, index=False)

        return (
            f"=== PEIRRO DATA REPORT ===\n"
            f"File: {os.path.basename(clean_path)}\n"
            f"Rows: {df.shape[0]} | Columns: {df.shape[1]}\n"
            f"Duplicates Removed: {dupes_removed}\n"
            f"Missing Values Imputed: {null_summary}\n"
            f"Clean Dataset Saved: {out_path}\n\n"
            f"=== STATISTICAL INSIGHTS ===\n{df.describe().to_string()}"
        )
    except Exception as e:
        return f"Data analysis failed: {str(e)}"
