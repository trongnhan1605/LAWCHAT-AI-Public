"""Backend tool execution package for LawChat-AI."""

from src.tools.check_validity import ValidityCheckResult, evaluate_document_validity
from src.tools.get_related_articles import RelatedArticleResult, get_related_articles
from src.tools.resolve_conflict import ConflictResolutionResult, resolve_document_conflict
from src.tools.search_law import SearchLawResult, search_law

__all__ = [
	"ValidityCheckResult",
	"ConflictResolutionResult",
	"SearchLawResult",
	"RelatedArticleResult",
	"evaluate_document_validity",
	"get_related_articles",
	"resolve_document_conflict",
	"search_law",
]
