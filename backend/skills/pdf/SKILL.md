---
name: pdf_document_analysis
description: >
  Skill for reading and analyzing PDF documents. Provides code snippets for
  extracting text, tables, and metadata from PDF files using PyMuPDF.
  Use when source documents include .pdf files.
triggers:
  file_types: [".pdf"]
  keywords: ["pdf", "document", "report", "paper"]
---

# PDF Document Analysis Skill

## Quick Start — Extract Text

```python
import fitz  # PyMuPDF

doc = fitz.open('document.pdf')
print(f"Pages: {len(doc)}")

text = ""
for page in doc:
    text += page.get_text()
print(text[:2000])
```

## Extract Text with Page Markers

```python
import fitz

doc = fitz.open('document.pdf')
for i, page in enumerate(doc):
    text = page.get_text("text")
    print(f"\n=== Page {i+1} ===")
    print(text)
```

## Extract Tables from PDFs

```python
import fitz

doc = fitz.open('document.pdf')
for page_num, page in enumerate(doc):
    tables = page.find_tables()
    for j, table in enumerate(tables):
        data = table.extract()
        if data:
            print(f"Table {j+1} on page {page_num+1}:")
            for row in data[:5]:
                print(row)
```

## Extract Metadata

```python
import fitz

doc = fitz.open('document.pdf')
meta = doc.metadata
print(f"Title: {meta.get('title', 'N/A')}")
print(f"Author: {meta.get('author', 'N/A')}")
print(f"Pages: {len(doc)}")
print(f"Created: {meta.get('creationDate', 'N/A')}")
```

## Search for Text in PDF

```python
import fitz

doc = fitz.open('document.pdf')
search_term = "revenue"
for i, page in enumerate(doc):
    results = page.search_for(search_term)
    if results:
        text = page.get_text()
        print(f"Found '{search_term}' on page {i+1} ({len(results)} hits)")
        idx = text.lower().find(search_term.lower())
        if idx >= 0:
            start = max(0, idx - 100)
            end = min(len(text), idx + 200)
            print(f"  ...{text[start:end]}...")
```

## Analysis Guidelines

### Understanding PDF Extraction
- **Column layouts**: Text may be extracted across columns, mixing content.
  Look for topic shifts mid-paragraph as a sign of column extraction.
- **Headers/footers**: Repeated text at page boundaries — filter when aggregating.
- **Tables**: May appear as irregular spacing. Use find_tables() for structured extraction.
- **Figures/images**: Not extracted as text — note reference gaps.

### Document Structure
- Identify document type: academic paper, business report, legal document, manual
- Map logical structure: abstract → introduction → body → conclusion
- Note numbered sections, appendices, and cross-references

### Content Synthesis
- Weigh executive summaries and conclusions more heavily for key findings
- Cross-reference claims in body with data in appendices
- Track defined terms and acronyms through the document
- Distinguish between primary findings and cited third-party data

### Report Integration
- Reference source documents by name and page: "According to [filename], p.3-5..."
- If figures were present but not extracted, note: "Source contains visual data on page X"
- Maintain the source document's level of certainty — don't overclaim
