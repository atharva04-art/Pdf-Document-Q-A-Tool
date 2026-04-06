# utils/pdf_processor.py

"""
PDF processing utilities for the PDF Q&A prototype.

This module handles:
1. Extracting text from PDF with page numbers
2. Cleaning the text
3. Chunking the text into overlapping pieces
4. Combining all steps into one pipeline
"""

import re
from typing import List, Dict
from PyPDF2 import PdfReader


def extract_text_from_pdf(uploaded_file) -> List[Dict]:
    """
    Extract text page by page from uploaded PDF file.

    Args:
        uploaded_file: Streamlit uploaded PDF file object

    Returns:
        List[Dict]: [{"page": 1, "text": "..."}]
    """
    reader = PdfReader(uploaded_file)
    pages_data = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text and page_text.strip():
            pages_data.append({
                "page": page_num,
                "text": page_text
            })

    return pages_data


def clean_text(text: str) -> str:
    """
    Clean extracted text.

    Args:
        text (str): Raw extracted text

    Returns:
        str: Cleaned text
    """
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def chunk_text(pages_data: List[Dict], chunk_size: int = 600, overlap: int = 100) -> List[Dict]:
    """
    Split page text into overlapping chunks while preserving page number.

    Args:
        pages_data (List[Dict]): [{"page": 1, "text": "..."}]
        chunk_size (int): Approximate number of words per chunk
        overlap (int): Number of overlapping words

    Returns:
        List[Dict]: [{"page": 1, "chunk_text": "..."}]
    """
    all_chunks = []

    for page_item in pages_data:
        page_num = page_item["page"]
        cleaned = clean_text(page_item["text"])
        words = cleaned.split()

        if not words:
            continue

        start = 0
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            all_chunks.append({
                "page": page_num,
                "chunk_text": chunk_text
            })

            start += chunk_size - overlap

    return all_chunks


def process_pdf(uploaded_file, chunk_size: int = 600, overlap: int = 100) -> List[Dict]:
    """
    Full PDF processing pipeline.

    Returns:
        List[Dict]: [{"page": page_number, "chunk_text": "..."}]
    """
    pages_data = extract_text_from_pdf(uploaded_file)
    chunks = chunk_text(pages_data, chunk_size=chunk_size, overlap=overlap)
    return chunks