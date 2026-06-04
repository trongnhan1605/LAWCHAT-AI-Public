import type { Locale } from "../../locales";
import { translateAdminTabLabel } from "../../locales/metadata";
import type { AdminTab } from "./types";

type RoadmapPhaseStatus = "verified" | "partially_verified" | "in_progress" | "planned";

type RoadmapPhaseItem = {
  code: string;
  title: string;
  dependencies: string;
  effortHours: number;
  progressPercent: number;
  deliveredArtifacts: string;
  acceptanceCriteria: string;
  checkLocation: AdminTab;
  status: RoadmapPhaseStatus;
};

const ROADMAP_PHASES: RoadmapPhaseItem[] = [
  {
    code: "GĐ 0",
    title: "Chốt phương án",
    dependencies: "13; nền cho 5-9",
    effortHours: 24,
    progressPercent: 100,
    deliveredArtifacts: "Blueprint; roadmap; gap analysis",
    acceptanceCriteria: "Tài liệu kiến trúc được chốt và dùng làm mốc triển khai.",
    checkLocation: "roadmap",
    status: "verified",
  },
  {
    code: "GĐ 1",
    title: "Nền dữ liệu",
    dependencies: "1, 5, 6, 9",
    effortHours: 88,
    progressPercent: 80,
    deliveredArtifacts: "OCR pipeline; ingest; metadata model; chunk/vector; diagnostics; quality scoring",
    acceptanceCriteria: "Tài liệu thật upload được, OCR ra text, có metadata, chunk/vector và chỉ số chất lượng để kiểm tra.",
    checkLocation: "documents",
    status: "partially_verified",
  },
  {
    code: "GĐ 2",
    title: "Annotation & bảo mật",
    dependencies: "2, 3, 2004",
    effortHours: 72,
    progressPercent: 25,
    deliveredArtifacts: "De-identification spec; schema nhãn; annotation / ground-truth format",
    acceptanceCriteria: "Legal team có thể bắt đầu batch gán nhãn thử, export dữ liệu và đối chiếu ground-truth.",
    checkLocation: "annotation",
    status: "in_progress",
  },
  {
    code: "GĐ 3",
    title: "Parse cấu trúc",
    dependencies: "4, 5, 8, 9",
    effortHours: 128,
    progressPercent: 75,
    deliveredArtifacts: "legal_provisions; provision_relations; parser score; pending review cho AI fallback",
    acceptanceCriteria: "Một tài liệu sinh được cấu trúc điều khoản, quan hệ điều khoản, có thể phân tích lại cấu trúc và xem diagnostics trên dashboard.",
    checkLocation: "documents",
    status: "partially_verified",
  },
  {
    code: "GĐ 4",
    title: "Search & RAG",
    dependencies: "6, 7, 2009",
    effortHours: 96,
    progressPercent: 65,
    deliveredArtifacts: "Vector search; retrieval API; citation grounding; RAG validation",
    acceptanceCriteria: "Tìm kiếm và trả lời có căn cứ điều/khoản; citation được kiểm tra; answer yếu bị chặn hoặc gắn cờ.",
    checkLocation: "ai-settings",
    status: "in_progress",
  },
  {
    code: "GĐ 5",
    title: "Citator & validation",
    dependencies: "7, 8, 2009",
    effortHours: 104,
    progressPercent: 50,
    deliveredArtifacts: "Validity tools; conflict rules; citation benchmark suite",
    acceptanceCriteria: "Kiểm tra được hiệu lực, sửa đổi, điều khoản liên quan và chất lượng dẫn chứng trên bộ câu hỏi mẫu.",
    checkLocation: "logs",
    status: "in_progress",
  },
  {
    code: "GĐ 6",
    title: "Graph & Neo4j",
    dependencies: "5, 8, 9, 13",
    effortHours: 80,
    progressPercent: 60,
    deliveredArtifacts: "Neo4j backend; graph backend routing; parity API; benchmark API",
    acceptanceCriteria: "Chuyển được giữa relational và Neo4j; graph mẫu khớp về node/edge; có benchmark/parity để đối chiếu.",
    checkLocation: "ai-settings",
    status: "in_progress",
  },
  {
    code: "GĐ 7",
    title: "Orchestration",
    dependencies: "7, 8, 9, 13",
    effortHours: 112,
    progressPercent: 35,
    deliveredArtifacts: "Orchestration flow; reasoning payload; escalation flow",
    acceptanceCriteria: "Chat đi đủ bước phân tích, truy xuất, kiểm tra và escalation khi case khó.",
    checkLocation: "logs",
    status: "in_progress",
  },
  {
    code: "GĐ 8",
    title: "Ứng dụng luật sư",
    dependencies: "10, 11, 12",
    effortHours: 144,
    progressPercent: 10,
    deliveredArtifacts: "Template module; risk review; summarization module",
    acceptanceCriteria: "Có bản chạy thử cho template, rà soát hợp đồng và tóm tắt hồ sơ.",
    checkLocation: "overview",
    status: "planned",
  },
  {
    code: "GĐ 9",
    title: "Vận hành & release",
    dependencies: "9, 13; hỗ trợ 1-12",
    effortHours: 88,
    progressPercent: 70,
    deliveredArtifacts: "Ops dashboard; benchmark/diagnostics; logs; tickets; regression suite",
    acceptanceCriteria: "Dashboard dùng được cho kiểm thử, vận hành, benchmark và kiểm tra trước bàn giao.",
    checkLocation: "logs",
    status: "partially_verified",
  },
];

function translateRoadmapStatus(locale: Locale, status: RoadmapPhaseStatus): string {
  if (locale === "vi") {
    return {
      verified: "Đã xác minh",
      partially_verified: "Xác minh một phần",
      in_progress: "Đang làm",
      planned: "Kế hoạch",
    }[status];
  }
  return {
    verified: "Verified",
    partially_verified: "Partially verified",
    in_progress: "In progress",
    planned: "Planned",
  }[status];
}

export function RoadmapSection({ locale, onTabChange }: { locale: Locale; onTabChange: (tab: AdminTab) => void }) {
  const verifiedCount = ROADMAP_PHASES.filter((item) => item.status === "verified").length;
  const partiallyVerifiedCount = ROADMAP_PHASES.filter((item) => item.status === "partially_verified").length;
  const inProgressCount = ROADMAP_PHASES.filter((item) => item.status === "in_progress").length;
  const averageProgress = Math.round(ROADMAP_PHASES.reduce((sum, item) => sum + item.progressPercent, 0) / ROADMAP_PHASES.length);

  return (
    <div className="admin-overview-shell">
      <div className="admin-hero-card admin-hero-card-modern">
        <div className="admin-hero-copy-block">
          <p className="section-label">{locale === "vi" ? "Lộ trình triển khai" : "Implementation roadmap"}</p>
          <h3>{locale === "vi" ? "Theo dõi phase, tiến độ và chỗ cần kiểm tra" : "Track phases, progress, and where to verify each one"}</h3>
          <p>
            {locale === "vi"
              ? "Bảng này gom đúng các giai đoạn kỹ thuật, artifact đã có và tiêu chí nghiệm thu để đối chiếu trực tiếp với dashboard hiện tại."
              : "This board groups the implementation phases, current artifacts, and acceptance criteria so they can be checked directly against the current dashboard."}
          </p>
        </div>
        <div className="admin-hero-badges admin-hero-metrics">
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Đã xác minh" : "Verified"}</span>
            <strong>{verifiedCount}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Xác minh một phần" : "Partially verified"}</span>
            <strong>{partiallyVerifiedCount}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Đang làm" : "In progress"}</span>
            <strong>{inProgressCount}</strong>
          </div>
          <div className="admin-hero-metric-pill">
            <span>{locale === "vi" ? "Tiến độ TB" : "Avg progress"}</span>
            <strong>{averageProgress}%</strong>
          </div>
        </div>
      </div>

      <div className="admin-table-section">
        <div className="admin-table-wrap">
          <table className="admin-table admin-table-compact">
            <thead>
              <tr>
                <th>{locale === "vi" ? "Giai đoạn" : "Phase"}</th>
                <th>{locale === "vi" ? "Phụ thuộc" : "Dependencies"}</th>
                <th>{locale === "vi" ? "Effort" : "Effort"}</th>
                <th>{locale === "vi" ? "Tiến độ" : "Progress"}</th>
                <th>{locale === "vi" ? "Trạng thái" : "Status"}</th>
                <th>{locale === "vi" ? "Artifact đã có" : "Delivered artifacts"}</th>
                <th>{locale === "vi" ? "Tiêu chí nghiệm thu" : "Acceptance criteria"}</th>
                <th>{locale === "vi" ? "Chỗ kiểm tra" : "Check in UI"}</th>
              </tr>
            </thead>
            <tbody>
              {ROADMAP_PHASES.map((phase) => (
                <tr key={phase.code}>
                  <td className="admin-table-title-cell">
                    <div className="admin-table-title">{phase.code} - {phase.title}</div>
                  </td>
                  <td>{phase.dependencies}</td>
                  <td>{phase.effortHours}h</td>
                  <td>{phase.progressPercent}%</td>
                  <td>
                    <span className={`document-chip ${
                      phase.status === "verified"
                        ? "active-chip"
                        : phase.status === "partially_verified"
                          ? "draft-chip"
                          : phase.status === "in_progress"
                            ? "pending-chip"
                            : "inactive-chip"
                    }`}>
                      {translateRoadmapStatus(locale, phase.status)}
                    </span>
                  </td>
                  <td>{phase.deliveredArtifacts}</td>
                  <td>{phase.acceptanceCriteria}</td>
                  <td>
                    <button className="ghost-button" onClick={() => onTabChange(phase.checkLocation)} type="button">
                      {translateAdminTabLabel(locale, phase.checkLocation)}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
