import json

from sqlalchemy.orm import Session

from src.models.authority_level_definition import AuthorityLevelDefinition
from src.models.article_concept_link import ArticleConceptLink
from src.models.category import Category
from src.models.content_article import ContentArticle
from src.models.document import Document
from src.models.document_type_definition import DocumentTypeDefinition
from src.models.lawyer_profile import LawyerProfile
from src.models.legal_concept import LegalConcept
from src.models.legal_concept_alias import LegalConceptAlias
from src.models.legal_concept_edge import LegalConceptEdge
from src.services.legal_metadata_parser_service import legal_metadata_parser_service

DEFAULT_CATEGORIES = [
    ("Bảo hiểm", "bao-hiem", "Tư vấn bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm nhân thọ và tranh chấp bảo hiểm."),
    ("Dân sự", "dan-su", "Giao dịch dân sự, hợp đồng vay, tài sản, bồi thường và tranh chấp dân sự."),
    ("Lao động", "lao-dong", "Quy định chung về quan hệ lao động, hợp đồng, tiền lương, thời giờ làm việc, kỷ luật và tranh chấp lao động."),
    ("Hôn nhân và gia đình", "hon-nhan-va-gia-dinh", "Quy định về kết hôn, ly hôn, nuôi con, chia tài sản và quan hệ gia đình."),
    ("Đất đai", "dat-dai", "Quy định về quyền sử dụng đất, thu hồi đất, bồi thường và hồ sơ đất đai."),
    ("Doanh nghiệp", "doanh-nghiep", "Thành lập, vận hành, hợp đồng, quản trị và tranh chấp doanh nghiệp."),
    ("Giao thông - Vận tải", "giao-thong-van-tai", "Xử phạt giao thông, vận tải, giấy phép và trách nhiệm khi xảy ra tai nạn."),
    ("Hành chính", "hanh-chinh", "Khiếu nại, tố cáo, thủ tục hành chính và quan hệ với cơ quan nhà nước."),
    ("Hình sự", "hinh-su", "Tư vấn tố giác, bị can, bị cáo, người bị hại và trách nhiệm hình sự."),
    ("Sở hữu trí tuệ", "so-huu-tri-tue", "Nhãn hiệu, bản quyền, sáng chế, bí mật kinh doanh và xử lý xâm phạm."),
    ("Thừa kế - Di chúc", "thua-ke-di-chuc", "Lập di chúc, khai nhận di sản, phân chia thừa kế và tranh chấp di sản."),
    ("Thuế", "thue", "Nghĩa vụ thuế cá nhân, doanh nghiệp, hóa đơn, kê khai và xử phạt thuế."),
]

DEFAULT_DOCUMENT_TYPES = [
    ("Bộ luật", "bo-luat", "Nhóm bộ luật có hiệu lực pháp lý cao trong hệ thống văn bản.", 100),
    ("Luật", "luat", "Luật do Quốc hội ban hành.", 95),
    ("Nghị quyết", "nghi-quyet", "Nghị quyết của cơ quan có thẩm quyền.", 90),
    ("Nghị định", "nghi-dinh", "Nghị định của Chính phủ.", 80),
    ("Thông tư", "thong-tu", "Thông tư hướng dẫn thi hành.", 70),
    ("Quyết định", "quyet-dinh", "Quyết định hành chính hoặc điều hành.", 60),
    ("Chỉ thị", "chi-thi", "Chỉ thị điều hành hoặc hướng dẫn.", 55),
    ("Án lệ", "an-le", "Án lệ được công bố.", 50),
    ("Khác", "khac", "Các loại văn bản khác.", 40),
]

DEFAULT_AUTHORITY_LEVELS = [
    ("Quốc hội", "quoc-hoi", "Cơ quan lập pháp cao nhất.", 1),
    ("Ủy ban Thường vụ Quốc hội", "uy-ban-thuong-vu-quoc-hoi", "Cơ quan thường trực của Quốc hội.", 2),
    ("Chính phủ", "chinh-phu", "Cơ quan hành chính nhà nước cao nhất.", 3),
    ("Thủ tướng Chính phủ", "thu-tuong-chinh-phu", "Người đứng đầu Chính phủ.", 4),
    ("Hội đồng Thẩm phán TANDTC", "hoi-dong-tham-phan-tandtc", "Cơ quan ban hành nghị quyết hướng dẫn xét xử.", 5),
    ("Tòa án nhân dân tối cao", "toa-an-nhan-dan-toi-cao", "Cơ quan xét xử cao nhất.", 6),
    ("Viện kiểm sát nhân dân tối cao", "vien-kiem-sat-nhan-dan-toi-cao", "Cơ quan kiểm sát cao nhất.", 7),
    ("Bộ", "bo", "Cơ quan cấp bộ.", 8),
    ("Ủy ban nhân dân", "uy-ban-nhan-dan", "Cơ quan hành chính địa phương.", 9),
    ("Khác", "khac", "Các nhóm cơ quan khác.", 10),
]

DEFAULT_CONTENT_ARTICLES = [
    ("Thông báo chấm dứt hợp đồng lao động", "thong-bao-cham-dut-hop-dong-lao-dong", "Lao động", "Các điểm cần kiểm tra khi người lao động hoặc doanh nghiệp muốn kết thúc quan hệ lao động đúng thủ tục.", "https://i-law.vn/huong-dan-phap-ly/thong-bao-cham-dut-hop-dong-lao-dong-66863", True),
    ("Quy định về hợp đồng lao động", "quy-dinh-ve-hop-dong-lao-dong", "Lao động", "Tổng quan hình thức hợp đồng, nghĩa vụ khi giao kết và các lưu ý thường gặp trong quan hệ lao động.", "https://i-law.vn/huong-dan-phap-ly/quy-dinh-ve-hop-dong-lao-dong-67995", True),
    ("Thủ tục ly hôn mới nhất", "thu-tuc-ly-hon-moi-nhat", "Hôn nhân", "Tóm lược trình tự nộp hồ sơ, tạm ứng án phí và các bước tòa án xử lý yêu cầu ly hôn.", "https://i-law.vn/huong-dan-phap-ly/thu-tuc-ly-hon-moi-nhat-nam-2020-67582", True),
    ("Thừa kế theo pháp luật là gì?", "thua-ke-theo-phap-luat-la-gi", "Dân sự", "Giải thích khi nào di sản được chia theo pháp luật và cách xác định hàng thừa kế theo Bộ luật Dân sự.", "https://i-law.vn/huong-dan-phap-ly/thua-ke-theo-phap-luat-la-gi-68514", False),
]

DEFAULT_LAWYER_PROFILES = [
    ("Luật sư Nguyễn Minh Anh", "luat-su-nguyen-minh-anh", "Luật sư tư vấn doanh nghiệp", "TP. Hồ Chí Minh", "Doanh nghiệp, hợp đồng, lao động", 9, "9.4", "Tư vấn cấu trúc hợp đồng, quản trị rủi ro pháp lý và tranh chấp lao động cho doanh nghiệp vừa và nhỏ.", "", True),
    ("Luật sư Trần Quốc Việt", "luat-su-tran-quoc-viet", "Luật sư tranh tụng dân sự", "Hà Nội", "Dân sự, đất đai, thừa kế", 12, "9.2", "Hỗ trợ khách hàng trong tranh chấp tài sản, hồ sơ đất đai, thừa kế và đại diện làm việc tại tòa án.", "", True),
    ("Luật sư Lê Hoàng Yến", "luat-su-le-hoang-yen", "Luật sư hôn nhân gia đình", "Đà Nẵng", "Hôn nhân, gia đình, trẻ em", 7, "9.0", "Tư vấn ly hôn, nuôi con, chia tài sản chung và các vấn đề bảo vệ quyền lợi gia đình.", "", True),
]

DEFAULT_LEGAL_CONCEPTS = [
    {
        "slug": "nha-dau-tu-nuoc-ngoai",
        "canonical_name": "Nhà đầu tư nước ngoài",
        "concept_type": "entity_type",
        "legal_domain": "dat-dai",
        "description": "Chủ thể đầu tư nước ngoài thực hiện hoạt động đầu tư tại Việt Nam.",
        "aliases": [
            "nhà đầu tư nước ngoài",
            "nha dau tu nuoc ngoai",
            "foreign investor",
        ],
    },
    {
        "slug": "thanh-lap-doanh-nghiep-tai-viet-nam",
        "canonical_name": "Thành lập doanh nghiệp tại Việt Nam",
        "concept_type": "procedure",
        "legal_domain": "dat-dai",
        "description": "Thủ tục hoặc hành vi pháp lý dẫn tới việc hình thành doanh nghiệp có vốn đầu tư nước ngoài.",
        "aliases": [
            "thành lập doanh nghiệp tại việt nam",
            "thanh lap doanh nghiep tai viet nam",
            "thành lập doanh nghiệp",
            "thanh lap doanh nghiep",
            "thành lập công ty",
            "thanh lap cong ty",
        ],
    },
    {
        "slug": "doanh-nghiep-co-von-dau-tu-nuoc-ngoai",
        "canonical_name": "Doanh nghiệp có vốn đầu tư nước ngoài (FDI)",
        "concept_type": "entity_type",
        "legal_domain": "dat-dai",
        "description": "Tổ chức kinh tế có vốn đầu tư nước ngoài hoạt động tại Việt Nam.",
        "aliases": [
            "doanh nghiệp có vốn đầu tư nước ngoài",
            "doanh nghiep co von dau tu nuoc ngoai",
            "doanh nghiệp fdi",
            "doanh nghiep fdi",
            "tổ chức kinh tế có vốn đầu tư nước ngoài",
            "to chuc kinh te co von dau tu nuoc ngoai",
        ],
    },
    {
        "slug": "quyen-su-dung-dat",
        "canonical_name": "Quyền sử dụng đất",
        "concept_type": "asset",
        "legal_domain": "dat-dai",
        "description": "Quyền của chủ thể trong việc sử dụng đất theo pháp luật đất đai.",
        "aliases": [
            "quyền sử dụng đất",
            "quyen su dung dat",
            "nhận chuyển nhượng quyền sử dụng đất",
            "nhan chuyen nhuong quyen su dung dat",
            "land use rights",
        ],
    },
]

DEFAULT_LEGAL_CONCEPT_EDGES = [
    {
        "source_slug": "nha-dau-tu-nuoc-ngoai",
        "target_slug": "thanh-lap-doanh-nghiep-tai-viet-nam",
        "edge_type": "REQUIRES_PROCEDURE",
        "label": "Thực hiện thủ tục thành lập doanh nghiệp",
        "legal_effect": "Nhà đầu tư nước ngoài muốn tham gia thị trường Việt Nam thường phải đi qua thủ tục thành lập hoặc tham gia tổ chức kinh tế phù hợp.",
        "confidence_score": 0.82,
    },
    {
        "source_slug": "thanh-lap-doanh-nghiep-tai-viet-nam",
        "target_slug": "doanh-nghiep-co-von-dau-tu-nuoc-ngoai",
        "edge_type": "CREATES_ENTITY",
        "label": "Hình thành doanh nghiệp FDI",
        "legal_effect": "Kết quả pháp lý của thủ tục là hình thành doanh nghiệp có vốn đầu tư nước ngoài hoặc tổ chức kinh tế liên quan.",
        "confidence_score": 0.9,
    },
    {
        "source_slug": "doanh-nghiep-co-von-dau-tu-nuoc-ngoai",
        "target_slug": "quyen-su-dung-dat",
        "edge_type": "ENABLES_RIGHT",
        "label": "Có thể phát sinh quyền về đất theo điều kiện luật đất đai",
        "legal_effect": "Doanh nghiệp FDI có thể có hoặc bị hạn chế quyền sử dụng đất tùy theo cấu trúc pháp lý và điều kiện luật đất đai áp dụng.",
        "confidence_score": 0.86,
    },
]

DEFAULT_CONCEPT_DOCUMENT_LINKS = [
    {
        "concept_slug": "nha-dau-tu-nuoc-ngoai",
        "document_markers": ("luat dau tu",),
        "relation_role": "sets_condition",
        "source_excerpt": "Luật Đầu tư là nguồn chính để xác định điều kiện của nhà đầu tư nước ngoài.",
    },
    {
        "concept_slug": "doanh-nghiep-co-von-dau-tu-nuoc-ngoai",
        "document_markers": ("luat doanh nghiep",),
        "relation_role": "defines",
        "source_excerpt": "Luật Doanh nghiệp là nguồn chính để xác định cấu trúc doanh nghiệp và tổ chức kinh tế.",
    },
    {
        "concept_slug": "quyen-su-dung-dat",
        "document_markers": ("luat dat dai",),
        "relation_role": "grants_right",
        "source_excerpt": "Luật Đất đai là nguồn chính để xác định quyền và hạn chế liên quan đến quyền sử dụng đất.",
    },
]

def ensure_seed_data(db: Session) -> None:
    for name, slug, description in DEFAULT_CATEGORIES:
        exists = db.query(Category).filter(Category.slug == slug).first()
        if exists is None:
            db.add(Category(name=name, slug=slug, description=description))
        else:
            exists.name = name
            exists.description = description

    for name, slug, description, normative_level in DEFAULT_DOCUMENT_TYPES:
        exists = db.query(DocumentTypeDefinition).filter(DocumentTypeDefinition.slug == slug).first()
        if exists is None:
            db.add(DocumentTypeDefinition(name=name, slug=slug, description=description, normative_level=normative_level))
        else:
            exists.name = name
            exists.description = description
            exists.normative_level = normative_level

    for name, slug, description, hierarchy_rank in DEFAULT_AUTHORITY_LEVELS:
        exists = db.query(AuthorityLevelDefinition).filter(AuthorityLevelDefinition.slug == slug).first()
        if exists is None:
            db.add(AuthorityLevelDefinition(name=name, slug=slug, description=description, hierarchy_rank=hierarchy_rank))
        else:
            exists.name = name
            exists.description = description
            exists.hierarchy_rank = hierarchy_rank

    for title, slug, category, excerpt, source_url, is_featured in DEFAULT_CONTENT_ARTICLES:
        exists = db.query(ContentArticle).filter(ContentArticle.slug == slug).first()
        if exists is None:
            db.add(ContentArticle(title=title, slug=slug, category=category, excerpt=excerpt, source_url=source_url, is_featured=is_featured, is_active=True))

    for full_name, slug, title, location, specialties, experience_years, rating, bio, avatar_url, is_featured in DEFAULT_LAWYER_PROFILES:
        exists = db.query(LawyerProfile).filter(LawyerProfile.slug == slug).first()
        if exists is None:
            db.add(LawyerProfile(full_name=full_name, slug=slug, title=title, location=location, specialties=specialties, experience_years=experience_years, rating=rating, bio=bio, avatar_url=avatar_url or None, is_featured=is_featured, is_active=True))

    concept_by_slug: dict[str, LegalConcept] = {}
    for item in DEFAULT_LEGAL_CONCEPTS:
        exists = db.query(LegalConcept).filter(LegalConcept.slug == item["slug"]).first()
        if exists is None:
            exists = LegalConcept(
                slug=item["slug"],
                canonical_name=item["canonical_name"],
                concept_type=item["concept_type"],
                legal_domain=item["legal_domain"],
                description=item["description"],
                is_seed=True,
                is_active=True,
            )
            db.add(exists)
            db.flush()
        else:
            exists.canonical_name = item["canonical_name"]
            exists.concept_type = item["concept_type"]
            exists.legal_domain = item["legal_domain"]
            exists.description = item["description"]
            exists.is_seed = True
            exists.is_active = True
        concept_by_slug[item["slug"]] = exists

        existing_aliases = db.query(LegalConceptAlias).filter(LegalConceptAlias.concept_id == exists.id).all()
        seen_aliases = {alias.alias_text for alias in existing_aliases}
        for index, alias_text in enumerate(item["aliases"]):
            if alias_text in seen_aliases:
                continue
            db.add(
                LegalConceptAlias(
                    concept_id=exists.id,
                    alias_text=alias_text,
                    alias_type="canonical" if index == 0 else "synonym",
                    is_primary=index == 0,
                )
            )

    db.flush()

    for item in DEFAULT_LEGAL_CONCEPT_EDGES:
        source = concept_by_slug.get(item["source_slug"])
        target = concept_by_slug.get(item["target_slug"])
        if source is None or target is None:
            continue
        exists = (
            db.query(LegalConceptEdge)
            .filter(
                LegalConceptEdge.source_concept_id == source.id,
                LegalConceptEdge.target_concept_id == target.id,
                LegalConceptEdge.edge_type == item["edge_type"],
            )
            .first()
        )
        if exists is None:
            db.add(
                LegalConceptEdge(
                    source_concept_id=source.id,
                    target_concept_id=target.id,
                    edge_type=item["edge_type"],
                    label=item["label"],
                    legal_effect=item["legal_effect"],
                    confidence_score=item["confidence_score"],
                    is_active=True,
                    metadata_json=json.dumps({"seed": True}, ensure_ascii=False),
                )
            )
        else:
            exists.label = item["label"]
            exists.legal_effect = item["legal_effect"]
            exists.confidence_score = item["confidence_score"]
            exists.is_active = True

    db.flush()

    normalized_documents = [
        (document, legal_metadata_parser_service.normalize_search_text(f"{document.title} {document.document_code or ''}"))
        for document in db.query(Document).filter(Document.is_active.is_(True)).all()
    ]
    for item in DEFAULT_CONCEPT_DOCUMENT_LINKS:
        concept = concept_by_slug.get(item["concept_slug"])
        if concept is None:
            continue
        matched_document = next(
            (
                document
                for document, normalized in normalized_documents
                if any(marker in normalized for marker in item["document_markers"])
            ),
            None,
        )
        if matched_document is None:
            continue
        exists = (
            db.query(ArticleConceptLink)
            .filter(
                ArticleConceptLink.concept_id == concept.id,
                ArticleConceptLink.document_id == matched_document.id,
                ArticleConceptLink.relation_role == item["relation_role"],
            )
            .first()
        )
        metadata_json = json.dumps({"seed": True, "source_excerpt": item["source_excerpt"]}, ensure_ascii=False)
        if exists is None:
            db.add(
                ArticleConceptLink(
                    concept_id=concept.id,
                    document_id=matched_document.id,
                    chunk_id=None,
                    relation_role=item["relation_role"],
                    confidence_score=0.8,
                    metadata_json=metadata_json,
                    is_active=True,
                )
            )
        else:
            exists.metadata_json = metadata_json
            exists.confidence_score = 0.8
            exists.is_active = True

    db.commit()
