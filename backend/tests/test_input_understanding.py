from src.orchestration.input_understanding import legal_input_understanding, normalize_legal_text


def test_normalize_legal_text_removes_vietnamese_accents() -> None:
    assert normalize_legal_text("Tranh chấp quyền sử dụng đất") == "tranh chap quyen su dung dat"


def test_input_understanding_detects_land_high_risk_query() -> None:
    result = legal_input_understanding.analyze("Tôi bị thu hồi đất và đang tranh chấp bồi thường.")

    assert result.detected_domain == "dat-dai"
    assert result.detected_intent == "legal_qa"
    assert result.complexity_level == "high"
    assert result.normalized_content == "toi bi thu hoi dat va dang tranh chap boi thuong."


def test_input_understanding_detects_validity_intent() -> None:
    result = legal_input_understanding.analyze("Văn bản này còn hiệu lực không?")

    assert result.detected_domain == "hon-nhan-va-gia-dinh"
    assert result.detected_intent == "validity_check"
    assert result.complexity_level == "low"
