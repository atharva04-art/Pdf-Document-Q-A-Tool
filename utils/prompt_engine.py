# utils/prompt_engine.py

from typing import List, Tuple


def format_context(retrieved_chunks: List[Tuple[str, float, int, int]]) -> str:
    """
    Format retrieved chunks into context block.

    Each tuple:
    (chunk_text, score, chunk_index, page_number)
    """
    formatted = []

    for i, (chunk, score, idx, page_num) in enumerate(retrieved_chunks, start=1):
        formatted.append(
            f"[SOURCE {i} | Page: {page_num} | Chunk ID: {idx} | Similarity: {score:.4f}]\n{chunk}"
        )

    return "\n\n".join(formatted)


def build_basic_prompt(question: str, context: str) -> str:
    return f"""
You are a helpful AI assistant answering questions from a PDF document.

Use ONLY the provided document context to answer the question.

If the answer is not present in the context, say:
"Not enough information in the document."

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

Instructions:
- Answer clearly and directly
- Mention page number(s) if visible in sources
- Do not invent facts
"""


def build_cot_prompt(question: str, context: str) -> str:
    return f"""
You are an expert document analysis assistant.

Use ONLY the provided context.

If answer is not present, say:
"Not enough information in the document."

DOCUMENT CONTEXT:
{context}

QUESTION:
{question}

OUTPUT FORMAT:
Reasoning Summary:
<brief reasoning>

Final Answer:
<answer with page reference if possible>
"""


def build_grounded_fewshot_prompt(question: str, context: str) -> str:
    return f"""
You are a strict retrieval-grounded document question answering system.

Your ONLY job is to answer using the provided document context.

STRICT RULES:
1. Use ONLY the exact information in the context
2. Do NOT use outside knowledge
3. Do NOT infer beyond what is explicitly written
4. If the answer is not directly supported, say exactly:
   "Not enough information in the document."
5. Summarize cleanly instead of listing too many repetitive points
6. Keep the answer concise, professional, and factual
7. Always include evidence and source references
8. ALWAYS mention page number(s) from the source

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{question}

REQUIRED OUTPUT FORMAT:

Answer:
<2-4 sentence grounded answer>

Evidence:
- <short supporting point from document>
- <short supporting point from document>

Sources:
SOURCE 1 (Page X), SOURCE 2 (Page Y)

If answer is not directly available, output exactly:

Answer:
Not enough information in the document.

Evidence:
- No directly supporting text found.

Sources:
None
"""


def get_prompt(question: str, context: str, prompt_type: str = "grounded_fewshot") -> str:
    prompt_type = prompt_type.lower().strip()

    if prompt_type == "basic":
        return build_basic_prompt(question, context)
    elif prompt_type == "cot":
        return build_cot_prompt(question, context)
    else:
        return build_grounded_fewshot_prompt(question, context)


def get_available_prompt_types():
    return {
        "basic": "Basic Zero-Shot",
        "cot": "Chain-of-Thought"
    }