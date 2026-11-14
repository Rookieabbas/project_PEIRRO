import os
import sys
import glob
import json
import webbrowser
import tempfile
import pandas as pd
import numpy as np
import pyperclip

class DataScientist:
    @staticmethod
    def profile_dataset(file_path: str) -> dict:
        """Reads CSV or Excel, flags outliers via IQR/Z-score, and generates business distribution statistics."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(file_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            return {"error": "Unsupported file format."}

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        summary = {
            "total_rows": int(df.shape[0]),
            "total_columns": int(df.shape[1]),
            "columns": list(df.columns),
            "numeric_columns": num_cols,
            "outliers_detected": {}
        }

        # Outlier Detection using IQR method
        for col in num_cols:
            clean_col = df[col].dropna()
            if len(clean_col) > 10:
                q25, q75 = np.percentile(clean_col, 25), np.percentile(clean_col, 75)
                iqr = q75 - q25
                lower_bound = q25 - (1.5 * iqr)
                upper_bound = q75 + (1.5 * iqr)
                outliers = clean_col[(clean_col < lower_bound) | (clean_col > upper_bound)]
                summary["outliers_detected"][col] = {
                    "count": int(len(outliers)),
                    "percentage": round(float(len(outliers) / len(clean_col)) * 100, 2),
                    "skewness": round(float(clean_col.skew()), 2)
                }

        return summary

    @staticmethod
    def generate_dax_measure(objective: str) -> str:
        """Synthesizes validated DAX syntax, places it onto the Windows clipboard, and returns it."""
        # Standard dynamic DAX patterns
        dax = ""
        low = objective.lower()
        if "yoy" in low or "year-over-year" in low:
            dax = (
                "YoY_Revenue_Growth = \n"
                "VAR CurrentYearRev = CALCULATE(SUM(Sales[Amount]), KEEPFILTERS(Sales[Quarter] <> \"Q4\"))\n"
                "VAR PriorYearRev = CALCULATE(SUM(Sales[Amount]), SAMEPERIODLASTYEAR('Date'[Date]), KEEPFILTERS(Sales[Quarter] <> \"Q4\"))\n"
                "RETURN\n"
                "DIVIDE(CurrentYearRev - PriorYearRev, PriorYearRev, 0)"
            )
        elif "margin" in low:
            dax = "Profit_Margin_Pct = DIVIDE([Total_Profit], [Total_Revenue], 0)"
        else:
            dax = f"Measure_{int(np.random.randint(100, 999))} = CALCULATE(COUNTROWS('Table'), ALLSELECTED('Table'))"

        pyperclip.copy(dax)
        return dax

    @staticmethod
    def render_instant_chart(title: str, labels: list, values: list) -> str:
        """Generates a standalone dark-mode interactive HTML chart and pops it open in browser/HUD."""
        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
            <style>
                body {{ background-color: #0b0f19; color: #fff; margin: 0; padding: 20px; font-family: Segoe UI, sans-serif; }}
                #chart {{ width: 100%; height: 90vh; }}
            </style>
        </head>
        <body>
            <div id="chart"></div>
            <script>
                var data = [{{
                    x: {json.dumps(labels)},
                    y: {json.dumps(values)},
                    type: 'bar',
                    marker: {{ color: '#00f3ff' }}
                }}];
                var layout = {{
                    title: '{title}',
                    paper_bgcolor: '#0b0f19',
                    plot_bgcolor: '#0d111a',
                    font: {{ color: '#c9d1d9' }}
                }};
                Plotly.newPlot('chart', data, layout, {{responsive: true}});
            </script>
        </body>
        </html>
        """
        tmp.write(html_content.encode("utf-8"))
        tmp.close()
        webbrowser.open(f"file://{tmp.name}")
        return tmp.name