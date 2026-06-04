from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.article_concept_link import ArticleConceptLink
from src.models.document import Document
from src.models.document_relation import DocumentRelation
from src.models.legal_concept import LegalConcept
from src.models.legal_concept_alias import LegalConceptAlias
from src.models.legal_concept_edge import LegalConceptEdge
from src.models.legal_provision import LegalProvision
from src.models.provision_relation import ProvisionRelation
from src.services.legal_metadata_parser_service import legal_metadata_parser_service
from src.services.neo4j_graph_service import neo4j_graph_service


@dataclass(slots=True)
class Neo4jProjectionSyncSummary:
    mode: str
    document_id: int | None
    document_count: int
    provision_count: int
    document_relation_count: int
    provision_relation_count: int


class Neo4jProjectionService:
    batch_size = 100

    def sync_all(self, db: Session) -> Neo4jProjectionSyncSummary:
        neo4j_graph_service._ensure_neo4j_ready()

        documents = db.query(Document).filter(Document.is_active.is_(True)).all()
        provisions = db.query(LegalProvision).filter(LegalProvision.is_active.is_(True)).all()
        document_relations = db.query(DocumentRelation).filter(DocumentRelation.is_active.is_(True)).all()
        provision_relations = db.query(ProvisionRelation).filter(ProvisionRelation.is_active.is_(True)).all()
        concepts = db.query(LegalConcept).filter(LegalConcept.is_active.is_(True)).all()
        concept_aliases = db.query(LegalConceptAlias).all()
        concept_edges = db.query(LegalConceptEdge).filter(LegalConceptEdge.is_active.is_(True)).all()
        article_concept_links = db.query(ArticleConceptLink).filter(ArticleConceptLink.is_active.is_(True)).all()

        driver = neo4j_graph_service._driver()
        with driver.session(database=neo4j_graph_service.backend_overview()["database"]) as session:
            session.execute_write(self._ensure_schema)
            session.execute_write(self._wipe_graph)
            self._execute_in_batches(session, self._upsert_documents, documents)
            self._execute_in_batches(session, self._upsert_provisions, provisions)
            self._execute_in_batches(session, self._upsert_document_relations, document_relations)
            self._execute_in_batches(session, self._upsert_provision_relations, provision_relations)
            self._execute_in_batches(session, self._upsert_concepts, self._build_concept_rows(concepts, concept_aliases))
            self._execute_in_batches(session, self._upsert_concept_edges, concept_edges)
            self._execute_in_batches(session, self._upsert_article_concept_links, article_concept_links)

        return Neo4jProjectionSyncSummary(
            mode="full",
            document_id=None,
            document_count=len(documents),
            provision_count=len(provisions),
            document_relation_count=len(document_relations),
            provision_relation_count=len(provision_relations),
        )

    def sync_document(self, db: Session, document_id: int) -> Neo4jProjectionSyncSummary:
        neo4j_graph_service._ensure_neo4j_ready()

        documents = (
            db.query(Document)
            .filter(Document.is_active.is_(True), Document.id == document_id)
            .all()
        )
        if not documents:
            return Neo4jProjectionSyncSummary(
                mode="document",
                document_id=document_id,
                document_count=0,
                provision_count=0,
                document_relation_count=0,
                provision_relation_count=0,
            )

        document_relations = (
            db.query(DocumentRelation)
            .filter(
                DocumentRelation.is_active.is_(True),
                (DocumentRelation.source_document_id == document_id) | (DocumentRelation.target_document_id == document_id),
            )
            .all()
        )
        related_document_ids = {document_id}
        for relation in document_relations:
            related_document_ids.add(relation.source_document_id)
            related_document_ids.add(relation.target_document_id)

        documents = (
            db.query(Document)
            .filter(Document.is_active.is_(True), Document.id.in_(related_document_ids))
            .all()
        )
        provisions = (
            db.query(LegalProvision)
            .filter(LegalProvision.is_active.is_(True), LegalProvision.document_id.in_(related_document_ids))
            .all()
        )
        provision_relations = (
            db.query(ProvisionRelation)
            .filter(
                ProvisionRelation.is_active.is_(True),
                (ProvisionRelation.source_document_id.in_(related_document_ids))
                & (ProvisionRelation.target_document_id.in_(related_document_ids)),
            )
            .all()
        )
        article_concept_links = (
            db.query(ArticleConceptLink)
            .filter(
                ArticleConceptLink.is_active.is_(True),
                ArticleConceptLink.document_id.in_(related_document_ids),
            )
            .all()
        )
        concept_ids = sorted({item.concept_id for item in article_concept_links})
        concepts = []
        concept_edges = []
        if concept_ids:
            concepts = (
                db.query(LegalConcept)
                .filter(LegalConcept.is_active.is_(True), LegalConcept.id.in_(concept_ids))
                .all()
            )
            concept_aliases = (
                db.query(LegalConceptAlias)
                .filter(LegalConceptAlias.concept_id.in_(concept_ids))
                .all()
            )
            concept_edges = (
                db.query(LegalConceptEdge)
                .filter(
                    LegalConceptEdge.is_active.is_(True),
                    LegalConceptEdge.source_concept_id.in_(concept_ids),
                    LegalConceptEdge.target_concept_id.in_(concept_ids),
                )
                .all()
            )

        driver = neo4j_graph_service._driver()
        with driver.session(database=neo4j_graph_service.backend_overview()["database"]) as session:
            session.execute_write(self._ensure_schema)
            session.execute_write(self._delete_documents_subgraph, list(related_document_ids))
            self._execute_in_batches(session, self._upsert_documents, documents)
            self._execute_in_batches(session, self._upsert_provisions, provisions)
            self._execute_in_batches(session, self._upsert_document_relations, document_relations)
            self._execute_in_batches(session, self._upsert_provision_relations, provision_relations)
            self._execute_in_batches(session, self._upsert_concepts, self._build_concept_rows(concepts, concept_aliases))
            self._execute_in_batches(session, self._upsert_concept_edges, concept_edges)
            self._execute_in_batches(session, self._upsert_article_concept_links, article_concept_links)

        return Neo4jProjectionSyncSummary(
            mode="document",
            document_id=document_id,
            document_count=len(documents),
            provision_count=len(provisions),
            document_relation_count=len(document_relations),
            provision_relation_count=len(provision_relations),
        )

    def _wipe_graph(self, tx) -> None:
        tx.run("MATCH (n) DETACH DELETE n")

    def _ensure_schema(self, tx) -> None:
        tx.run("CREATE CONSTRAINT document_document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.document_id IS UNIQUE")
        tx.run("CREATE CONSTRAINT provision_provision_id_unique IF NOT EXISTS FOR (p:Provision) REQUIRE p.provision_id IS UNIQUE")
        tx.run("CREATE CONSTRAINT concept_concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE")
        tx.run("CREATE INDEX provision_document_id_idx IF NOT EXISTS FOR (p:Provision) ON (p.document_id)")
        tx.run("CREATE INDEX concept_slug_idx IF NOT EXISTS FOR (c:Concept) ON (c.slug)")

    def _execute_in_batches(self, session, callback, items: list[object]) -> None:
        if not items:
            return
        for start in range(0, len(items), self.batch_size):
            session.execute_write(callback, items[start : start + self.batch_size])

    def _delete_documents_subgraph(self, tx, document_ids: list[int]) -> None:
        tx.run(
            """
            MATCH (d:Document)
            WHERE d.document_id IN $document_ids
            OPTIONAL MATCH (d)-[:HAS_PROVISION]->(p:Provision)
            DETACH DELETE d, p
            """,
            document_ids=document_ids,
        )

    def _upsert_documents(self, tx, documents: list[Document]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MERGE (d:Document {document_id: row.document_id})
            SET d.title = row.title,
                d.document_code = row.document_code,
                d.document_type = row.document_type,
                d.issuing_authority = row.issuing_authority,
                d.legal_status = row.legal_status,
                d.legal_domain = row.legal_domain,
                d.effective_date = row.effective_date,
                d.expiry_date = row.expiry_date
            """,
            rows=[
                {
                    "document_id": item.id,
                    "title": item.title,
                    "document_code": item.document_code,
                    "document_type": item.document_type,
                    "issuing_authority": item.issuing_authority,
                    "legal_status": item.legal_status,
                    "legal_domain": item.legal_domain,
                    "effective_date": item.effective_date.isoformat() if item.effective_date else None,
                    "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                }
                for item in documents
            ],
        )

    def _upsert_provisions(self, tx, provisions: list[LegalProvision]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MERGE (p:Provision {provision_id: row.provision_id})
            SET p.document_id = row.document_id,
                p.parent_provision_id = row.parent_provision_id,
                p.provision_level = row.provision_level,
                p.article_number = row.article_number,
                p.clause_number = row.clause_number,
                p.point_code = row.point_code,
                p.heading = row.heading,
                p.citation_label = row.citation_label,
                p.legal_status = row.legal_status,
                p.sort_key = row.sort_key
            WITH p, row
            MATCH (d:Document {document_id: row.document_id})
            MERGE (d)-[:HAS_PROVISION]->(p)
            """,
            rows=[
                {
                    "provision_id": item.id,
                    "document_id": item.document_id,
                    "parent_provision_id": item.parent_provision_id,
                    "provision_level": item.provision_level,
                    "article_number": item.article_number,
                    "clause_number": item.clause_number,
                    "point_code": item.point_code,
                    "heading": item.heading,
                    "citation_label": item.citation_label,
                    "legal_status": item.legal_status,
                    "sort_key": item.sort_key,
                }
                for item in provisions
            ],
        )
        tx.run(
            """
            UNWIND $rows AS row
            WITH row WHERE row.parent_provision_id IS NOT NULL
            MATCH (parent:Provision {provision_id: row.parent_provision_id})
            MATCH (child:Provision {provision_id: row.provision_id})
            MERGE (parent)-[:HAS_CHILD_PROVISION]->(child)
            """,
            rows=[
                {"provision_id": item.id, "parent_provision_id": item.parent_provision_id}
                for item in provisions
                if item.parent_provision_id is not None
            ],
        )

    def _upsert_document_relations(self, tx, relations: list[DocumentRelation]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (source:Document {document_id: row.source_document_id})
            MATCH (target:Document {document_id: row.target_document_id})
            MERGE (source)-[r:RELATES_TO {relation_id: row.relation_id}]->(target)
            SET r.relation_type = row.relation_type,
                r.relation_label = row.relation_label,
                r.legal_basis = row.legal_basis,
                r.confidence_score = row.confidence_score
            """,
            rows=[
                {
                    "relation_id": item.id,
                    "source_document_id": item.source_document_id,
                    "target_document_id": item.target_document_id,
                    "relation_type": item.relation_type,
                    "relation_label": item.relation_label,
                    "legal_basis": item.legal_basis,
                    "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                }
                for item in relations
            ],
        )

    def _upsert_provision_relations(self, tx, relations: list[ProvisionRelation]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (source:Provision {provision_id: row.source_provision_id})
            MATCH (target:Provision {provision_id: row.target_provision_id})
            MERGE (source)-[r:PROVISION_RELATES_TO {relation_id: row.relation_id}]->(target)
            SET r.relation_type = row.relation_type,
                r.relation_label = row.relation_label,
                r.confidence_score = row.confidence_score,
                r.extraction_method = row.extraction_method
            """,
            rows=[
                {
                    "relation_id": item.id,
                    "source_provision_id": item.source_provision_id,
                    "target_provision_id": item.target_provision_id,
                    "relation_type": item.relation_type,
                    "relation_label": item.relation_label,
                    "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                    "extraction_method": item.extraction_method,
                }
                for item in relations
            ],
        )

    def _build_concept_rows(self, concepts: list[LegalConcept], aliases: list[LegalConceptAlias]) -> list[dict[str, object]]:
        aliases_by_concept_id: dict[int, list[str]] = {}
        for alias in aliases:
            aliases_by_concept_id.setdefault(alias.concept_id, []).append(alias.alias_text)

        rows = []
        for item in concepts:
            concept_aliases = aliases_by_concept_id.get(item.id, [])
            normalized_aliases = sorted(
                {
                    legal_metadata_parser_service.normalize_search_text(alias_text)
                    for alias_text in concept_aliases
                    if alias_text
                }
            )
            rows.append(
                {
                    "concept_id": item.id,
                    "slug": item.slug,
                    "canonical_name": item.canonical_name,
                    "canonical_name_normalized": legal_metadata_parser_service.normalize_search_text(item.canonical_name),
                    "aliases": concept_aliases,
                    "aliases_normalized": normalized_aliases,
                    "concept_type": item.concept_type,
                    "legal_domain": item.legal_domain,
                    "description": item.description,
                    "is_seed": item.is_seed,
                }
            )
        return rows

    def _upsert_concepts(self, tx, concept_rows: list[dict[str, object]]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MERGE (c:Concept {concept_id: row.concept_id})
            SET c.slug = row.slug,
                c.canonical_name = row.canonical_name,
                c.canonical_name_normalized = row.canonical_name_normalized,
                c.aliases = row.aliases,
                c.aliases_normalized = row.aliases_normalized,
                c.concept_type = row.concept_type,
                c.legal_domain = row.legal_domain,
                c.description = row.description,
                c.is_seed = row.is_seed
            """,
            rows=concept_rows,
        )

    def _upsert_concept_edges(self, tx, edges: list[LegalConceptEdge]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (source:Concept {concept_id: row.source_concept_id})
            MATCH (target:Concept {concept_id: row.target_concept_id})
            MERGE (source)-[r:SEMANTIC_RELATES_TO {edge_id: row.edge_id}]->(target)
            SET r.edge_type = row.edge_type,
                r.label = row.label,
                r.legal_effect = row.legal_effect,
                r.confidence_score = row.confidence_score,
                r.metadata_json = row.metadata_json
            """,
            rows=[
                {
                    "edge_id": item.id,
                    "source_concept_id": item.source_concept_id,
                    "target_concept_id": item.target_concept_id,
                    "edge_type": item.edge_type,
                    "label": item.label,
                    "legal_effect": item.legal_effect,
                    "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                    "metadata_json": item.metadata_json,
                }
                for item in edges
            ],
        )

    def _upsert_article_concept_links(self, tx, links: list[ArticleConceptLink]) -> None:
        tx.run(
            """
            UNWIND $rows AS row
            MATCH (d:Document {document_id: row.document_id})
            MATCH (c:Concept {concept_id: row.concept_id})
            MERGE (d)-[r:MENTIONS_CONCEPT {anchor_id: row.anchor_id}]->(c)
            SET r.chunk_id = row.chunk_id,
                r.relation_role = row.relation_role,
                r.confidence_score = row.confidence_score,
                r.metadata_json = row.metadata_json
            """,
            rows=[
                {
                    "anchor_id": item.id,
                    "document_id": item.document_id,
                    "concept_id": item.concept_id,
                    "chunk_id": item.chunk_id,
                    "relation_role": item.relation_role,
                    "confidence_score": float(item.confidence_score) if item.confidence_score is not None else None,
                    "metadata_json": item.metadata_json,
                }
                for item in links
            ],
        )


neo4j_projection_service = Neo4jProjectionService()
