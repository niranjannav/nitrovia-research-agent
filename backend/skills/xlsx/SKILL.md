---
name: excel_data_analysis
description: >
  Skill for analyzing Excel spreadsheet data. Use when source documents include
  .xlsx or .xls files. Provides code snippets for reading, analyzing, and
  extracting insights from spreadsheet data using openpyxl and pandas.
triggers:
  file_types: [".xlsx", ".xls"]
  keywords: ["spreadsheet", "excel", "tabular", "data analysis", "pivot"]
---

# Excel Data Analysis Skill

## Quick Start — Reading Excel Files

```python
import openpyxl

wb = openpyxl.load_workbook('file.xlsx', data_only=True)
for sheet_name in wb.sheetnames:
    sheet = wb[sheet_name]
    print(f"Sheet: {sheet_name} ({sheet.max_row} rows x {sheet.max_column} cols)")
    for row in sheet.iter_rows(min_row=1, max_row=min(5, sheet.max_row), values_only=True):
        print(row)
```

## Data Analysis with pandas

```python
import pandas as pd

# Read all sheets
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)
for name, df in all_sheets.items():
    print(f"\n=== {name} ===")
    print(f"Shape: {df.shape}")
    print(df.describe())
    print(df.head())
```

## Extracting Statistics

```python
import pandas as pd

df = pd.read_excel('file.xlsx')

# Summary statistics for numeric columns
for col in df.select_dtypes(include='number').columns:
    print(f"{col}: min={df[col].min()}, max={df[col].max()}, "
          f"mean={df[col].mean():.2f}, median={df[col].median():.2f}")

# Value counts for categorical columns
for col in df.select_dtypes(include='object').columns:
    print(f"\n{col} distribution:")
    print(df[col].value_counts().head(10))
```

## Detecting Formulas

```python
import openpyxl

wb = openpyxl.load_workbook('file.xlsx')  # data_only=False to see formulas
sheet = wb.active
for row in sheet.iter_rows():
    for cell in row:
        if isinstance(cell.value, str) and cell.value.startswith('='):
            print(f"{cell.coordinate}: {cell.value}")
```

## Analysis Guidelines

### Data Quality Assessment
- Check columns with >20% empty cells as potentially unreliable
- Flag mixed-type columns (numbers mixed with text)
- Identify outliers using standard deviation from mean
- Report data completeness percentage

### Cross-Sheet Analysis
- Look for relationships between sheets (shared column names, ID references)
- Compare metrics across sheets (different time periods, regions)
- Synthesize findings across sheets

### Numerical Presentation
- Always include specific numbers ("increased 23%", not just "increased")
- Use comparisons: ratios, percentages, year-over-year changes
- Round appropriately: financial to 2 decimals, percentages to 1 decimal
- Present ranges when uncertain: "between X and Y"

## Report Integration
- Lead with the most impactful numerical findings
- Create data narratives: "The data shows X, which suggests Y"
- Cite which sheet and approximate row range data comes from
- Recommend visualizations: "This data would benefit from a bar chart"

## Presentation Slide Guidance
- Use `stat_callout` slides for key metrics (KPIs, totals, percentages)
- Use `comparison` slides for before/after or category comparisons
- Use `chart` slides with actual data_labels and data_values from the spreadsheet
- Limit tables on slides to 5 rows × 4 columns maximum
