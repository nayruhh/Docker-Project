"""Text helpers shared by the cache and the database layer."""


def normalize_question(question: str) -> str:
    """Lower-case and collapse whitespace so trivially different questions match.

    "What is  the capital of France?" and "what is the capital of france?" normalise to
    the same string. The original text is always stored separately.
    """
    return " ".join(question.casefold().split())
