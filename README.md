# Day 1 GitHub Repo Ingestion Project

This project demonstrates how to ingest documentation data from a public GitHub repository
using Python.

## Dataset
- Repository: https://github.com/openai/openai-cookbook
- File types: `.md`, `.mdx`

## Method
- Downloaded the repository as a ZIP file using `requests`
- Read files in memory using `zipfile`
- Parsed markdown files and extracted content using `python-frontmatter`

## Result
- Total documents ingested: 66

## Next Steps
- Clean and chunk the documents
- Prepare the data for search or RAG indexing
