import re
from collections.abc import Callable, Mapping
from typing import Any

from workspace import redact_sensitive_content


def _question_text(item: object) -> tuple[str, str, str]:
    if isinstance(item, str):
        return item.strip(), "", ""
    if isinstance(item, Mapping):
        question = item.get("question", "")
        if not isinstance(question, str):
            raise ValueError("Each open-question object must have a string 'question'.")
        reason = item.get("reason", item.get("why_it_matters", ""))
        default = item.get("suggested_default", "")
        return question.strip(), str(reason).strip(), str(default).strip()
    raise ValueError("Open questions must be strings or objects containing a string 'question'.")


def get_clarification_questions(requirements: Mapping[str, Any]) -> list[dict[str, str]]:
    raw_questions = requirements.get("open_questions", [])
    if isinstance(raw_questions, str):
        raw_questions = [raw_questions]
    if not isinstance(raw_questions, list):
        raise ValueError("Requirements 'open_questions' must be a list of questions.")

    questions: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw_questions:
        question, reason, default = _question_text(item)
        if not question:
            continue
        key = re.sub(r"\W+", " ", question).strip().casefold()
        if key not in seen:
            questions.append({"question": question, "reason": reason, "suggested_default": default})
            seen.add(key)

    requirement_text = " ".join(
        str(requirements.get(field, ""))
        for field in (
            "business_objectives",
            "project_type",
            "core_logic",
            "functional_requirements",
            "non_functional_requirements",
            "constraints",
            "acceptance_criteria",
        )
    ).casefold()
    existing_questions = " ".join(item["question"] for item in questions).casefold()

    def add_domain_question(
        question: str,
        reason: str,
        *,
        requirement_hints: tuple[str, ...],
        question_hints: tuple[str, ...],
    ) -> None:
        if any(hint in requirement_text for hint in requirement_hints):
            return
        if any(hint in existing_questions for hint in question_hints):
            return
        key = re.sub(r"\W+", " ", question).strip().casefold()
        if key not in seen:
            questions.append({"question": question, "reason": reason})
            seen.add(key)

    rag_project = any(
        term in requirement_text
        for term in ("rag", "retrieval-augmented", "retrieval augmented", "vector search", "bm25")
    )
    if rag_project:
        add_domain_question(
            "Which agents should handle which tasks, and how should requests be routed between them?",
            "The BRD asks for multi-agent orchestration but does not define agent roles or routing.",
            requirement_hints=("agent role", "agent responsibility", "routing rule", "task delegation"),
            question_hints=("agent role", "which agents", "agent responsibilities", "routing"),
        )
        add_domain_question(
            "What knowledge sources and file formats must be ingested, and what chunking and re-indexing rules should be used?",
            "The RAG indexing scope and lifecycle are not defined.",
            requirement_hints=("data source", "document format", "file format", "chunk size", "chunking strategy"),
            question_hints=("knowledge source", "document format", "chunk", "ingestion"),
        )
        add_domain_question(
            "Which embedding model and vector database should be used, or what constraints should guide that choice?",
            "The vector-search model and persistence layer affect quality, cost, and deployment.",
            requirement_hints=("embedding model", "vector database", "vector store", "vector index"),
            question_hints=("embedding", "vector store", "vector database"),
        )
        add_domain_question(
            "How should vector and BM25 results be combined, ranked, or reranked?",
            "The BRD requires hybrid retrieval but does not define its ranking or fusion behavior.",
            requirement_hints=("reciprocal rank", "rrf", "rerank", "re-rank", "fusion weight", "ranking strategy"),
            question_hints=("bm25", "hybrid retrieval", "ranking", "fusion", "rerank"),
        )
        add_domain_question(
            "Should answers include source citations, and what should happen when retrieved evidence is insufficient?",
            "Grounding and no-answer behavior are not specified for the RAG responses.",
            requirement_hints=("citation", "source attribution", "grounded answer", "insufficient evidence", "no answer"),
            question_hints=("citation", "grounded", "insufficient evidence", "no-answer"),
        )
        if re.search(r"\b\d+(?:\.\d+)?\s*%", requirement_text) and not any(
            term in requirement_text for term in ("baseline", "evaluation dataset", "evaluation set", "measurement method")
        ):
            add_domain_question(
                "What baseline, evaluation dataset, and retrieval-quality metric should verify the stated improvement target?",
                "The BRD states a percentage improvement without defining how to measure it.",
                requirement_hints=("baseline", "evaluation dataset", "evaluation set", "measurement method"),
                question_hints=("baseline", "evaluation dataset", "quality metric", "improvement target"),
            )
        if any(term in requirement_text for term in ("scalable", "scalability", "latency")) and not any(
            term in requirement_text for term in ("p95", "p99", "milliseconds", "requests per second", "concurrent users")
        ):
            add_domain_question(
                "What document volume, query rate/concurrency, and response-time targets define the required scale?",
                "The BRD mentions scalability or latency without measurable capacity targets.",
                requirement_hints=("p95", "p99", "milliseconds", "requests per second", "concurrent users"),
                question_hints=("query rate", "response-time target", "latency target", "capacity target"),
            )

    if not requirements.get("non_functional_requirements"):
        fallback = (
            "What non-functional targets should the application meet for performance, availability, "
            "security/privacy, and data retention?"
        )
        key = re.sub(r"\W+", " ", fallback).strip().casefold()
        if key not in seen:
            questions.append({"question": fallback, "reason": "No non-functional targets were specified."})
            seen.add(key)

    if not requirements.get("acceptance_criteria"):
        fallback = "What measurable acceptance criteria or examples will confirm the application is complete?"
        key = re.sub(r"\W+", " ", fallback).strip().casefold()
        if key not in seen:
            questions.append({"question": fallback, "reason": "No acceptance criteria were specified."})

    return questions


def ask_clarifying_questions(
    requirements: dict[str, Any],
    *,
    input_fn: Callable[[str], str] | None = None,
) -> list[dict[str, str]]:
    questions = get_clarification_questions(requirements)
    if not questions:
        return []

    read_input = input if input_fn is None else input_fn
    print("\nBefore generating code, please clarify these gaps in the requirements.")
    print("Press Enter to skip any question; skipped items will be treated as assumptions.")
    answers: list[dict[str, str]] = []
    for index, item in enumerate(questions, start=1):
        print(f"\n{index}. {item['question']}")
        if item.get("reason"):
            print(f"   Why it matters: {item['reason']}")
        if item.get("suggested_default"):
            print(f"   Suggested default: {item['suggested_default']}")
        answer = read_input("   Your answer (Enter to skip): ").strip()
        if answer:
            answers.append(
                {
                    "question": item["question"],
                    "answer": redact_sensitive_content(answer),
                }
            )

    requirements["clarification_answers"] = answers
    if answers:
        print(f"\nRecorded {len(answers)} clarification answer(s).")
    else:
        print("\nNo clarification answers provided; the generator will state its assumptions.")
    return answers
