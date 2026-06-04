import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import ChatWidget from "../components/ChatWidget";
import UserAccountMenu from "../components/UserAccountMenu";
import { useLawChatApp } from "../hooks/useLawChatApp";
import api from "../http/axios";
import type { ApiEnvelope, Category, ContentArticle, LawyerProfile } from "../types/lawchat";

const DEFAULT_CATEGORIES: Category[] = [
  { id: 1, name: "Lao động", slug: "lao-dong", description: "Hợp đồng, tiền lương, kỷ luật và tranh chấp lao động.", is_active: true },
  { id: 2, name: "Đất đai", slug: "dat-dai", description: "Quyền sử dụng đất, thu hồi đất và hồ sơ đất đai.", is_active: true },
  { id: 3, name: "Doanh nghiệp", slug: "doanh-nghiep", description: "Thành lập, vận hành, hợp đồng và tranh chấp doanh nghiệp.", is_active: true },
  { id: 4, name: "Thuế", slug: "thue", description: "Kê khai, nghĩa vụ thuế và xử phạt thuế.", is_active: true },
  { id: 5, name: "Bảo hiểm", slug: "bao-hiem", description: "Bảo hiểm xã hội, y tế và tranh chấp bảo hiểm.", is_active: true },
  { id: 6, name: "Đầu tư nước ngoài", slug: "dau-tu-nuoc-ngoai", description: "FDI, giấy phép đầu tư và tuân thủ tại Việt Nam.", is_active: true },
];

const DEFAULT_ARTICLES: ContentArticle[] = [
  {
    id: 1,
    category: "Lao động",
    title: "Thông báo chấm dứt hợp đồng lao động",
    slug: "thong-bao-cham-dut-hop-dong-lao-dong",
    excerpt: "Các điểm cần kiểm tra khi doanh nghiệp hoặc người lao động muốn kết thúc quan hệ lao động đúng thủ tục.",
    source_url: "https://i-law.vn/huong-dan-phap-ly/thong-bao-cham-dut-hop-dong-lao-dong-66863",
    is_featured: true,
    is_active: true,
    created_at: "",
    updated_at: "",
  },
  {
    id: 2,
    category: "Doanh nghiệp",
    title: "Rà soát rủi ro trước khi ký hợp đồng",
    slug: "ra-soat-rui-ro-hop-dong",
    excerpt: "Khung rà soát điều khoản, trách nhiệm và phương án xử lý tranh chấp cho doanh nghiệp.",
    source_url: null,
    is_featured: true,
    is_active: true,
    created_at: "",
    updated_at: "",
  },
  {
    id: 3,
    category: "Đất đai",
    title: "Hồ sơ chuyển nhượng quyền sử dụng đất",
    slug: "ho-so-chuyen-nhuong-dat",
    excerpt: "Tóm lược giấy tờ, nghĩa vụ tài chính và quy trình đăng ký biến động đất đai.",
    source_url: null,
    is_featured: true,
    is_active: true,
    created_at: "",
    updated_at: "",
  },
];

const DEFAULT_LAWYERS: LawyerProfile[] = [
  { id: 1, full_name: "Luật sư Nguyễn Minh Anh", slug: "luat-su-nguyen-minh-anh", title: "Doanh nghiệp & Lao động", location: "TP. Hồ Chí Minh", specialties: "Doanh nghiệp, hợp đồng, lao động", experience_years: 9, rating: "9.4", bio: "Tư vấn quản trị rủi ro pháp lý cho doanh nghiệp.", avatar_url: null, is_featured: true, is_active: true, created_at: "", updated_at: "" },
  { id: 2, full_name: "Luật sư Trần Quốc Việt", slug: "luat-su-tran-quoc-viet", title: "Dân sự & Đất đai", location: "Hà Nội", specialties: "Dân sự, đất đai, thừa kế", experience_years: 12, rating: "9.2", bio: "Tranh tụng và giải quyết tranh chấp tài sản.", avatar_url: null, is_featured: true, is_active: true, created_at: "", updated_at: "" },
  { id: 3, full_name: "Luật sư Lê Hoàng Yến", slug: "luat-su-le-hoang-yen", title: "Hôn nhân & Gia đình", location: "Đà Nẵng", specialties: "Hôn nhân, gia đình, trẻ em", experience_years: 7, rating: "9.0", bio: "Bảo vệ quyền lợi gia đình và trẻ em.", avatar_url: null, is_featured: true, is_active: true, created_at: "", updated_at: "" },
];

const LANDING_COPY = {
  vi: {
    nav: ["Trợ lý AI", "Cơ sở pháp luật", "Luật sư", "Gói dịch vụ"],
    login: "Đăng nhập",
    tryLawChat: "Dùng thử LawChat",
    eyebrow: "Trí tuệ pháp lý Việt Nam",
    heroLine1: "Hỏi pháp luật Việt Nam",
    heroLine2: "bằng ngôn ngữ tự nhiên",
    heroSummary: "Tra cứu quy định, phân tích vấn đề pháp lý và kết nối với luật sư phù hợp trên một nền tảng ứng dụng trí tuệ nhân tạo.",
    askLawChat: "Hỏi LawChat",
    vietnamLaw: "Pháp luật Việt Nam",
    searchPlaceholder: "Đặt câu hỏi về pháp luật Việt Nam...",
    citationPromise: "Câu trả lời kèm căn cứ pháp lý có thể kiểm chứng",
    tryAsking: "Câu hỏi gợi ý",
    suggestions: [
      "Công ty có được đơn phương chấm dứt hợp đồng lao động không?",
      "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
      "Nhà đầu tư nước ngoài có thể sở hữu bao nhiêu phần trăm vốn?",
    ],
    metrics: [
      ["20K+", "Văn bản pháp luật được lập chỉ mục"],
      ["98%", "Câu trả lời kèm căn cứ pháp lý"],
      ["< 8 giây", "Thời gian tra cứu trung bình"],
      ["120+", "Chuyên gia pháp lý đã xác minh"],
    ],
    demoHeading: ["Trợ lý pháp lý AI", "Từ câu hỏi đến câu trả lời có căn cứ", "LawChat xác định vấn đề pháp lý, tìm quy định áp dụng và chỉ rõ căn cứ cho từng kết luận."],
    currentMatter: "Vấn đề đang nghiên cứu",
    demoMenu: ["Chấm dứt hợp đồng lao động", "Văn bản nguồn", "Lịch sử tra cứu"],
    demoQuestion: "Người lao động có phải báo trước khi đơn phương chấm dứt hợp đồng lao động không xác định thời hạn không?",
    analysis: "Phân tích của LawChat",
    completed: "Hoàn tất trong 6,4 giây",
    answerIntro: <>Trong phần lớn trường hợp, người lao động có quyền đơn phương chấm dứt hợp đồng lao động không xác định thời hạn nhưng phải báo trước cho người sử dụng lao động ít nhất <mark>45 ngày</mark>. Một số trường hợp luật định cho phép chấm dứt mà không cần báo trước.</>,
    answerPoints: [
      ["Nguyên tắc chung", "Phải báo trước ít nhất 45 ngày."],
      ["Trường hợp ngoại lệ", "Có thể không cần báo trước khi người sử dụng lao động vi phạm một số nghĩa vụ theo luật định."],
    ],
    sources: "Căn cứ pháp lý",
    sourceItems: ["Bộ luật Lao động số 45/2019/QH14, điểm a khoản 1 Điều 35", "Bộ luật Lao động 2019, khoản 2 Điều 35"],
    legalNote: "Nội dung chỉ có giá trị tham khảo và cần được đối chiếu với tình tiết cụ thể của vụ việc.",
    featuresHeading: ["Một không gian làm việc pháp lý", "Hỗ trợ toàn bộ quy trình xử lý vấn đề pháp lý", "Đủ nhanh cho câu hỏi hằng ngày, đủ chặt chẽ cho hoạt động nghiên cứu chuyên nghiệp."],
    features: [
      ["Tra cứu pháp luật", "Tìm chính xác điều luật, nghị định và văn bản liên quan từ một câu hỏi tự nhiên."],
      ["Phân tích pháp lý", "Phân tích vấn đề theo dữ kiện, điều kiện áp dụng và các rủi ro pháp lý cần lưu ý."],
      ["Phân tích tài liệu", "Đọc, tóm tắt và phát hiện điều khoản đáng chú ý trong hợp đồng, hồ sơ pháp lý."],
      ["Kết nối luật sư", "Kết nối đúng luật sư theo chuyên môn, địa điểm và mức độ phức tạp của vụ việc."],
    ],
    exploreFeature: "Khám phá tính năng",
    workflowHeading: ["Quy trình hoạt động", "Từ vướng mắc pháp lý đến phương án xử lý rõ ràng", "Mỗi bước tra cứu đều minh bạch và có thể kiểm chứng."],
    workflow: [
      ["Đặt câu hỏi", "Trình bày vấn đề bằng ngôn ngữ tự nhiên."],
      ["Phân tích", "AI xác định vấn đề pháp lý và dữ kiện còn thiếu."],
      ["Dẫn chiếu", "Nhận câu trả lời kèm căn cứ pháp lý có thể kiểm chứng."],
      ["Kết nối", "Chuyển tiếp đến luật sư khi cần tư vấn chuyên sâu."],
    ],
    domainsHeading: ["Lĩnh vực pháp luật", "Pháp luật Việt Nam, được tổ chức theo nhu cầu thực tế", "Khám phá các lĩnh vực trọng yếu dựa trên hệ thống nguồn pháp luật có cấu trúc."],
    domains: [
      ["Lao động", "Hợp đồng lao động, tiền lương, chấm dứt hợp đồng và nghĩa vụ tại nơi làm việc."],
      ["Đất đai", "Quyền sử dụng đất, chuyển nhượng, quy hoạch và tranh chấp đất đai."],
      ["Doanh nghiệp", "Thành lập, quản trị, hợp đồng và tuân thủ pháp luật doanh nghiệp."],
      ["Thuế", "Nghĩa vụ thuế, kê khai, ưu đãi và xử phạt vi phạm hành chính về thuế."],
      ["Bảo hiểm", "Bảo hiểm xã hội, bảo hiểm y tế và tranh chấp về quyền lợi bảo hiểm."],
      ["Đầu tư nước ngoài", "Đầu tư trực tiếp nước ngoài, giấy phép, tỷ lệ sở hữu và tiếp cận thị trường."],
    ],
    lawyerEyebrow: "Kinh nghiệm con người, đúng lúc cần thiết",
    lawyerTitle: "Kết nối đúng luật sư, không chỉ là một luật sư bất kỳ.",
    lawyerCopy: "LawChat hỗ trợ chuẩn bị thông tin vụ việc trước, sau đó kết nối với luật sư đã được xác minh dựa trên lĩnh vực chuyên môn và kinh nghiệm.",
    findLawyer: "Tìm luật sư",
    years: "năm",
    lawyerRoles: ["Doanh nghiệp và Lao động", "Dân sự và Đất đai", "Hôn nhân và Gia đình"],
    blogHeading: ["Tri thức pháp lý", "Thông tin thực tiễn cho quyết định tốt hơn", "Cập nhật pháp luật, bài phân tích và hướng dẫn từ cơ sở tri thức của LawChat."],
    blogCards: [
      ["Lao động", "Thông báo chấm dứt hợp đồng lao động", "Các điểm cần kiểm tra khi doanh nghiệp hoặc người lao động muốn chấm dứt quan hệ lao động đúng quy định."],
      ["Doanh nghiệp", "Rà soát rủi ro trước khi ký hợp đồng", "Khung rà soát điều khoản, trách nhiệm và phương án xử lý tranh chấp dành cho doanh nghiệp."],
      ["Đất đai", "Hồ sơ chuyển nhượng quyền sử dụng đất", "Tóm lược giấy tờ, nghĩa vụ tài chính và quy trình đăng ký biến động đất đai."],
    ],
    readTime: "6 phút đọc",
    readArticle: "Đọc bài viết",
    ctaEyebrow: "Bắt đầu tra cứu với sự tin cậy",
    ctaTitle: "Trí tuệ pháp lý Việt Nam, sẵn sàng khi bạn cần.",
    ctaButton: "Dùng thử LawChat miễn phí",
    footerDescription: "Nền tảng tra cứu pháp luật bằng AI và kết nối chuyên gia pháp lý dành cho Việt Nam.",
    footerGroups: [["Sản phẩm", "Trợ lý AI", "Cơ sở pháp luật", "Luật sư"], ["Tài nguyên", "Cập nhật pháp luật", "Hướng dẫn tra cứu", "Gói dịch vụ"], ["Công ty", "Giới thiệu", "Bảo mật", "Liên hệ"]],
    copyright: "© 2026 LawChat-AI. Bảo lưu mọi quyền.",
    builtFor: "Được xây dựng cho hệ thống pháp luật Việt Nam.",
  },
  en: {
    nav: ["AI Assistant", "Legal Knowledge", "Lawyers", "Pricing"],
    login: "Login",
    tryLawChat: "Try LawChat",
    eyebrow: "Vietnam legal intelligence",
    heroLine1: "Ask Vietnamese Law",
    heroLine2: "in Natural Language",
    heroSummary: "Research regulations, analyze legal questions and connect with qualified lawyers on one AI-native platform.",
    askLawChat: "Ask LawChat",
    vietnamLaw: "Vietnam law",
    searchPlaceholder: "Ask a question about Vietnamese law...",
    citationPromise: "Answers include verifiable legal citations",
    tryAsking: "Try asking",
    suggestions: [
      "Can a company unilaterally terminate an employment contract?",
      "What are the conditions for transferring land use rights?",
      "How much equity may a foreign investor own?",
    ],
    metrics: [["20K+", "Legal documents indexed"], ["98%", "Answers with legal citations"], ["< 8 sec", "Average research time"], ["120+", "Verified legal experts"]],
    demoHeading: ["AI legal assistant", "From question to cited answer", "LawChat structures the issue, identifies applicable law and shows exactly where each conclusion comes from."],
    currentMatter: "Current matter",
    demoMenu: ["Employment termination", "Source documents", "Research history"],
    demoQuestion: "Do employees need to give notice before terminating an indefinite-term labor contract?",
    analysis: "LawChat analysis",
    completed: "Completed in 6.4s",
    answerIntro: <>In most cases, an employee may unilaterally terminate an indefinite-term labor contract by providing the employer with at least <mark>45 days&apos; prior notice</mark>. Certain statutory situations allow termination without prior notice.</>,
    answerPoints: [["General rule", "Provide at least 45 days' notice."], ["Exceptions", "No notice may be required for certain statutory employer violations."]],
    sources: "Legal sources",
    sourceItems: ["Labor Code No. 45/2019/QH14, Article 35(1)(a)", "Labor Code 2019, Article 35(2)"],
    legalNote: "This answer is informational and should be reviewed against the specific facts of the matter.",
    featuresHeading: ["One legal workspace", "Built for every step of legal work", "Fast enough for everyday questions, rigorous enough for professional research."],
    features: [["Legal Search", "Find relevant articles, decrees and legal instruments from a natural-language question."], ["Legal Reasoning", "Analyze facts, applicable conditions and legal risks that require attention."], ["Document Analysis", "Read, summarize and identify notable provisions in contracts and legal documents."], ["Lawyer Marketplace", "Connect with the right lawyer based on expertise, location and matter complexity."]],
    exploreFeature: "Explore feature",
    workflowHeading: ["How it works", "A clear path from uncertainty to action", "Designed to keep legal research transparent at every step."],
    workflow: [["Ask", "Describe the matter in natural language."], ["Analyze", "AI identifies the legal issues and missing facts."], ["Cite", "Receive an answer with verifiable legal sources."], ["Connect", "Escalate to a lawyer when expert advice is needed."]],
    domainsHeading: ["Knowledge domains", "Vietnamese law, organized around your work", "Explore key practice areas backed by structured legal sources."],
    domains: [["Labor", "Employment contracts, wages, termination and workplace obligations."], ["Land", "Land use rights, transfers, planning and land disputes."], ["Business", "Corporate formation, governance, contracts and compliance."], ["Tax", "Tax obligations, declarations, incentives and administrative penalties."], ["Insurance", "Social insurance, health insurance and benefit disputes."], ["Foreign investment", "FDI, licensing, ownership limits and market access."]],
    lawyerEyebrow: "Human expertise, when it matters",
    lawyerTitle: "Connect with the right lawyer, not just any lawyer.",
    lawyerCopy: "LawChat prepares the matter first, then connects you with verified lawyers based on practice area and experience.",
    findLawyer: "Find a lawyer",
    years: "yrs",
    lawyerRoles: ["Business and Labor", "Civil and Land", "Marriage and Family"],
    blogHeading: ["Legal intelligence", "Practical insights for better decisions", "Legal updates, explainers and research notes from the LawChat knowledge base."],
    blogCards: [
      ["Labor", "Notice requirements for terminating employment", "Key points employers and employees should check before ending an employment relationship."],
      ["Business", "Reviewing contractual risk before signing", "A practical framework for reviewing terms, liabilities and dispute-resolution options."],
      ["Land", "Documents required to transfer land use rights", "An overview of required documents, financial obligations and registration procedures."],
    ],
    readTime: "6 min read",
    readArticle: "Read article",
    ctaEyebrow: "Start researching with confidence",
    ctaTitle: "Vietnamese legal intelligence, ready when you are.",
    ctaButton: "Try LawChat for free",
    footerDescription: "AI-native legal research and expert connection for Vietnam.",
    footerGroups: [["Product", "AI Assistant", "Legal Knowledge", "Lawyers"], ["Resources", "Legal updates", "Research guides", "Pricing"], ["Company", "About", "Security", "Contact"]],
    copyright: "© 2026 LawChat-AI. All rights reserved.",
    builtFor: "Built for the Vietnamese legal system.",
  },
};

const FEATURE_ICONS = ["search", "reason", "document", "lawyer"];

type HomeContentPayload = {
  menu: Array<{ label: string; href: string }>;
  categories: Category[];
  articles: ContentArticle[];
  lawyers: LawyerProfile[];
};

export default function HomePage() {
  const navigate = useNavigate();
  const app = useLawChatApp();
  const t = LANDING_COPY[app.locale];
  const [query, setQuery] = useState("");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [homeContent, setHomeContent] = useState<HomeContentPayload>({
    menu: [],
    categories: DEFAULT_CATEGORIES,
    articles: DEFAULT_ARTICLES,
    lawyers: DEFAULT_LAWYERS,
  });

  useEffect(() => {
    let cancelled = false;
    api.get<ApiEnvelope<HomeContentPayload>>("/content/home")
      .then((response) => {
        if (!cancelled) {
          setHomeContent({
            menu: response.data.data.menu,
            categories: response.data.data.categories.length ? response.data.data.categories : DEFAULT_CATEGORIES,
            articles: response.data.data.articles.length ? response.data.data.articles : DEFAULT_ARTICLES,
            lawyers: response.data.data.lawyers.length ? response.data.data.lawyers : DEFAULT_LAWYERS,
          });
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  function askQuestion(question: string) {
    app.setDraft(question);
    app.setWidgetOpen(true);
  }

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = query.trim();
    if (normalized) {
      askQuestion(normalized);
    } else {
      navigate("/workspace");
    }
  }

  const articles = homeContent.articles.slice(0, 3);

  return (
    <main className="home-page ai-landing">
      <header className="ai-navbar">
        <button
          aria-expanded={isMobileMenuOpen}
          aria-haspopup="menu"
          aria-label={app.locale === "vi" ? "Mở menu" : "Open menu"}
          className="ai-mobile-menu-button"
          onClick={() => setIsMobileMenuOpen(true)}
          type="button"
        >
          <MenuIcon />
        </button>
        <a className="ai-brand" href="#top" aria-label={app.locale === "vi" ? "Trang chủ LawChat-AI" : "LawChat-AI home"}>
          <span className="ai-brand-mark">L</span>
          <span>LawChat<span className="ai-brand-dot">.ai</span></span>
        </a>

        <nav className="ai-nav-links" aria-label={app.locale === "vi" ? "Điều hướng chính" : "Main navigation"}>
          <a href="#ai-assistant">{t.nav[0]}</a>
          <a href="#knowledge">{t.nav[1]}</a>
          <a href="#lawyers">{t.nav[2]}</a>
          <a href="#pricing">{t.nav[3]}</a>
        </nav>

        <div className="ai-nav-actions">
          <div className="ai-locale-toggle" aria-label={app.locale === "vi" ? "Ngôn ngữ" : "Language"}>
            <button className={app.locale === "vi" ? "active" : ""} onClick={() => app.setLocale("vi")} type="button">VI</button>
            <button className={app.locale === "en" ? "active" : ""} onClick={() => app.setLocale("en")} type="button">EN</button>
          </div>
          <button className="ai-login-button" onClick={() => navigate("/login")} type="button">{t.login}</button>
          <button className="ai-nav-cta" onClick={() => navigate("/workspace")} type="button">{t.tryLawChat}</button>
          <UserAccountMenu locale={app.locale} />
        </div>
      </header>

      <div className={`ai-mobile-nav-backdrop ${isMobileMenuOpen ? "open" : ""}`} onClick={() => setIsMobileMenuOpen(false)} />
      <aside className={`ai-mobile-nav-drawer ${isMobileMenuOpen ? "open" : ""}`}>
        <div className="ai-mobile-nav-head">
          <a className="ai-brand" href="#top" onClick={() => setIsMobileMenuOpen(false)}>
            <span className="ai-brand-mark">L</span>
            <span>LawChat<span className="ai-brand-dot">.ai</span></span>
          </a>
          <button aria-label={app.locale === "vi" ? "Đóng menu" : "Close menu"} onClick={() => setIsMobileMenuOpen(false)} type="button"><CloseIcon /></button>
        </div>
        <nav aria-label={app.locale === "vi" ? "Điều hướng trên thiết bị di động" : "Mobile navigation"}>
          <a href="#ai-assistant" onClick={() => setIsMobileMenuOpen(false)}>{t.nav[0]}</a>
          <a href="#knowledge" onClick={() => setIsMobileMenuOpen(false)}>{t.nav[1]}</a>
          <a href="#lawyers" onClick={() => setIsMobileMenuOpen(false)}>{t.nav[2]}</a>
          <a href="#pricing" onClick={() => setIsMobileMenuOpen(false)}>{t.nav[3]}</a>
        </nav>
        <div className="ai-mobile-nav-footer">
          <div className="ai-locale-toggle" aria-label={app.locale === "vi" ? "Ngôn ngữ" : "Language"}>
            <button className={app.locale === "vi" ? "active" : ""} onClick={() => app.setLocale("vi")} type="button">VI</button>
            <button className={app.locale === "en" ? "active" : ""} onClick={() => app.setLocale("en")} type="button">EN</button>
          </div>
          <button className="ai-mobile-login" onClick={() => navigate("/login")} type="button">{t.login}</button>
          <button className="ai-nav-cta" onClick={() => navigate("/workspace")} type="button">{t.tryLawChat}</button>
        </div>
      </aside>

      <section className="ai-hero" id="top">
        <div className="ai-hero-content">
          <div className="ai-eyebrow"><span /> {t.eyebrow}</div>
          <h1>{t.heroLine1}<br /><em>{t.heroLine2}</em></h1>
          <p className="ai-hero-summary">{t.heroSummary}</p>

          <form className="ai-search-shell" onSubmit={handleSearch}>
            <div className="ai-search-topline">
              <SparkIcon />
              <span>{t.askLawChat}</span>
              <span className="ai-search-status">{t.vietnamLaw}</span>
            </div>
            <textarea
              aria-label={app.locale === "vi" ? "Đặt câu hỏi pháp lý" : "Ask a legal question"}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={t.searchPlaceholder}
              rows={3}
              value={query}
            />
            <div className="ai-search-footer">
              <span>{t.citationPromise}</span>
              <button aria-label={app.locale === "vi" ? "Gửi câu hỏi" : "Submit question"} type="submit"><ArrowIcon /></button>
            </div>
          </form>

          <div className="ai-suggestions" aria-label={app.locale === "vi" ? "Câu hỏi gợi ý" : "Suggested questions"}>
            <span>{t.tryAsking}</span>
            {t.suggestions.map((question) => (
              <button key={question} onClick={() => askQuestion(question)} type="button">{question}</button>
            ))}
          </div>
        </div>

        <div className="ai-proof-bar">
          {t.metrics.map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
        </div>
      </section>

      <section className="ai-section ai-demo-section" id="ai-assistant">
        <SectionHeading
          eyebrow={t.demoHeading[0]}
          title={t.demoHeading[1]}
          copy={t.demoHeading[2]}
        />

        <div className="ai-demo-window">
          <div className="ai-demo-sidebar">
            <div className="ai-demo-sidebar-head"><span className="ai-brand-mark">L</span><strong>Research</strong></div>
            <span className="ai-demo-label">{t.currentMatter}</span>
            {t.demoMenu.map((item, index) => <button className={index === 0 ? "active" : ""} key={item} type="button">{item}</button>)}
          </div>

          <div className="ai-demo-conversation">
            <div className="ai-demo-question">
              <span>Q</span>
              <p>{t.demoQuestion}</p>
            </div>
            <div className="ai-demo-answer">
              <div className="ai-answer-heading"><SparkIcon /><strong>{t.analysis}</strong><span>{t.completed}</span></div>
              <p>{t.answerIntro}</p>
              <div className="ai-answer-points">
                {t.answerPoints.map(([title, copy]) => <div key={title}><CheckIcon /><span><strong>{title}</strong> — {copy}</span></div>)}
              </div>
              <div className="ai-citations">
                <span>{t.sources}</span>
                {t.sourceItems.map((source, index) => <button key={source} type="button"><strong>{index + 1}</strong> {source}</button>)}
              </div>
              <p className="ai-answer-note">{t.legalNote}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="ai-section" id="knowledge">
        <SectionHeading
          eyebrow={t.featuresHeading[0]}
          title={t.featuresHeading[1]}
          copy={t.featuresHeading[2]}
        />
        <div className="ai-feature-grid">
          {t.features.map(([title, copy], index) => (
            <article className={`ai-feature-card feature-${index + 1}`} key={title}>
              <div className="ai-feature-icon"><FeatureIcon name={FEATURE_ICONS[index]} /></div>
              <span>0{index + 1}</span>
              <h3>{title}</h3>
              <p>{copy}</p>
              <button onClick={() => index === 3 ? document.querySelector("#lawyers")?.scrollIntoView({ behavior: "smooth" }) : navigate("/workspace")} type="button">
                {t.exploreFeature} <ArrowIcon />
              </button>
            </article>
          ))}
        </div>
      </section>

      <section className="ai-workflow-band">
        <div className="ai-section ai-workflow-inner">
          <SectionHeading
            eyebrow={t.workflowHeading[0]}
            title={t.workflowHeading[1]}
            copy={t.workflowHeading[2]}
            light
          />
          <div className="ai-workflow-grid">
            {t.workflow.map(([title, copy], index) => (
              <div className="ai-workflow-step" key={title}>
                <span>0{index + 1}</span>
                <h3>{title}</h3>
                <p>{copy}</p>
                {index < t.workflow.length - 1 ? <ArrowIcon /> : null}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="ai-section ai-domains-section">
        <SectionHeading
          eyebrow={t.domainsHeading[0]}
          title={t.domainsHeading[1]}
          copy={t.domainsHeading[2]}
        />
        <div className="ai-domain-grid">
          {t.domains.map(([name, description], index) => (
            <button key={name} onClick={() => askQuestion(app.locale === "vi" ? `Tôi cần tư vấn về ${name}` : `I need advice about ${name}`)} type="button">
              <span>0{index + 1}</span>
              <div><strong>{name}</strong><small>{description}</small></div>
              <ArrowIcon />
            </button>
          ))}
        </div>
      </section>

      <section className="ai-section ai-lawyer-section" id="lawyers">
        <div className="ai-lawyer-copy">
          <span className="ai-section-eyebrow">{t.lawyerEyebrow}</span>
          <h2>{t.lawyerTitle}</h2>
          <p>{t.lawyerCopy}</p>
          <button className="ai-dark-button" onClick={() => askQuestion(app.locale === "vi" ? "Tôi muốn tìm luật sư phù hợp với vấn đề của mình" : "I want to find the right lawyer for my matter")} type="button">{t.findLawyer} <ArrowIcon /></button>
        </div>
        <div className="ai-lawyer-list">
          {homeContent.lawyers.slice(0, 3).map((lawyer, index) => (
            <article key={lawyer.id}>
              <div className="ai-lawyer-avatar">{lawyer.full_name.split(" ").slice(-1)[0]?.charAt(0)}</div>
              <div><strong>{lawyer.full_name}</strong><span>{t.lawyerRoles[index] ?? lawyer.title}</span></div>
              <div className="ai-lawyer-score"><strong>{lawyer.rating ?? "9.0"}</strong><span>{lawyer.experience_years} {t.years}</span></div>
            </article>
          ))}
        </div>
      </section>

      <section className="ai-section ai-blog-section">
        <SectionHeading
          eyebrow={t.blogHeading[0]}
          title={t.blogHeading[1]}
          copy={t.blogHeading[2]}
        />
        <div className="ai-blog-grid">
          {articles.map((article, index) => {
            const [category, title, excerpt] = t.blogCards[index] ?? [article.category, article.title, article.excerpt];
            return (
            <a href={article.source_url ?? "#knowledge"} key={article.id} rel="noreferrer" target={article.source_url ? "_blank" : undefined}>
              <div className={`ai-blog-visual visual-${index + 1}`}><span>{category}</span><FeatureIcon name={index === 0 ? "document" : index === 1 ? "reason" : "search"} /></div>
              <span>{category} · {t.readTime}</span>
              <h3>{title}</h3>
              <p>{excerpt}</p>
              <strong>{t.readArticle} <ArrowIcon /></strong>
            </a>
            );
          })}
        </div>
      </section>

      <section className="ai-pricing-cta" id="pricing">
        <div>
          <span>{t.ctaEyebrow}</span>
          <h2>{t.ctaTitle}</h2>
        </div>
        <button onClick={() => navigate("/workspace")} type="button">{t.ctaButton} <ArrowIcon /></button>
      </section>

      <footer className="ai-footer">
        <div className="ai-footer-main">
          <div>
            <a className="ai-brand" href="#top"><span className="ai-brand-mark">L</span><span>LawChat<span className="ai-brand-dot">.ai</span></span></a>
            <p>{t.footerDescription}</p>
          </div>
          {t.footerGroups.map(([title, ...items], index) => (
            <div key={title}><strong>{title}</strong>{items.map((item) => <a href={index === 0 ? "#ai-assistant" : index === 1 ? "#knowledge" : "#top"} key={item}>{item}</a>)}</div>
          ))}
        </div>
        <div className="ai-footer-bottom"><span>{t.copyright}</span><span>{t.builtFor}</span></div>
      </footer>

      <div className="floating-widget-shell">
        <ChatWidget
          booting={app.booting}
          draft={app.draft}
          error={app.error}
          escalating={app.escalating}
          locale={app.locale}
          messages={app.widgetMessages}
          onDraftChange={app.setDraft}
          onEscalate={() => void app.handleEscalate()}
          onOpenWorkspace={() => navigate("/workspace")}
          onSubmit={app.handleSubmit}
          onToggleOpen={app.setWidgetOpen}
          open={app.widgetOpen}
          sending={app.sending}
          ui={app.ui}
        />
      </div>
    </main>
  );
}

function SectionHeading({ copy, eyebrow, light = false, title }: { copy: string; eyebrow: string; light?: boolean; title: string }) {
  return (
    <div className={`ai-section-heading ${light ? "light" : ""}`}>
      <span className="ai-section-eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{copy}</p>
    </div>
  );
}

function SparkIcon() {
  return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3zM19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7L19 16z" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.7" /></svg>;
}

function ArrowIcon() {
  return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M5 12h14M14 7l5 5-5 5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" /></svg>;
}

function CheckIcon() {
  return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M5 12.5l4 4L19 7" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" /></svg>;
}

function MenuIcon() {
  return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" /></svg>;
}

function CloseIcon() {
  return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" /></svg>;
}

function FeatureIcon({ name }: { name: string }) {
  if (name === "search") return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><circle cx="10.5" cy="10.5" r="5.5" stroke="currentColor" strokeWidth="1.7" /><path d="M15 15l5 5M8 9h5M8 12h3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.7" /></svg>;
  if (name === "reason") return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M12 4a6 6 0 00-3 11.2V19h6v-3.8A6 6 0 0012 4zM9 22h6M9 10h6M12 7v6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" /></svg>;
  if (name === "lawyer") return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M12 4v16M5 7h14M7 7l-4 7h8L7 7zM17 7l-4 7h8l-4-7zM8 20h8" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" /></svg>;
  return <svg aria-hidden="true" fill="none" viewBox="0 0 24 24"><path d="M7 3h7l4 4v14H7V3zM14 3v5h5M10 12h5M10 16h5" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" /></svg>;
}
