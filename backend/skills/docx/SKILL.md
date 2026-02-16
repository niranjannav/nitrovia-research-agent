---
name: docx_document_analysis
description: >
    Skill for reading and analyzing Word documents (.docx). Provides code snippets
    for extracting text, tables, and structure from DOCX files using python-docx.
    Use when source documents include .docx or .doc files.
triggers:
  file_types: [".docx", ".doc"]
  keywords: ["word", "document", "docx"]
---

# DOCX Document Analysis Skill

## Quick Start — Extract Text

```python
from docx import Document

doc = Document('document.docx')
for para in doc.paragraphs:
    if para.text.strip():
        print(f"[{para.style.name}] {para.text}")
```

## Extract with Structure

```python
from docx import Document

doc = Document('document.docx')
for para in doc.paragraphs:
    if para.style.name.startswith('Heading'):
        level = para.style.name.replace('Heading ', '')
        print(f"\n{'#' * int(level)} {para.text}")
    elif para.text.strip():
        print(para.text)
```

## Extract Tables

```python
from docx import Document

doc = Document('document.docx')
for i, table in enumerate(doc.tables):
    print(f"\nTable {i+1}:")
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        print(" | ".join(cells))
```

## Extract Document Metadata

```python
from docx import Document

doc = Document('document.docx')
props = doc.core_properties
print(f"Title: {props.title}")
print(f"Author: {props.author}")
print(f"Created: {props.created}")
print(f"Modified: {props.modified}")
print(f"Paragraphs: {len(doc.paragraphs)}")
print(f"Tables: {len(doc.tables)}")
```

## Search for Content

```python
from docx import Document

doc = Document('document.docx')
search_term = "conclusion"
for i, para in enumerate(doc.paragraphs):
    if search_term.lower() in para.text.lower():
        print(f"Paragraph {i} [{para.style.name}]: {para.text[:200]}")
```

## Analysis Guidelines
- Headings indicate document structure — use them to navigate content
- Tables often contain key data — always extract and analyze them
- Track numbering and cross-references
- Note images/charts referenced but not extractable as text
- Comments and tracked changes may contain important editorial context
