# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lương Quang Huy
- **MSSV:** 2A202602698
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/huyluong1910/K4-L3-DAY13-LuongQuangHuy-2A202602698-Monitoring-LLMOps
- **Commit SHA cuối:** 8ceed395b009e777bb4bd351293433d103f4ebeb
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602698`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Đạt toàn bộ: basic schema, correlation ID, enrichment context, PII scrubbing |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Cấu hình 6 panel YAML đạt chuẩn contract |
| `pytest` | 22 passed | 24 passed | 100% tests passed (đã bổ sung test scrub CCCD và thẻ tín dụng) |
| Số traces hợp lệ | 0 | 10+ | Đã tách child observations (retriever & generation), gắn correlation_id |
| Số PII leak | 0 | 0 | Không còn PII nguyên văn (được thay bằng [REDACTED_...]) |
| Latency P95 / TTFT P95 | 898.7 ms / 50 ms | 822.6 ms / 50.5 ms | P95 nằm sâu dưới ngưỡng SLO 3000ms |
| Retrieval success rate | 100% | 100% | Toàn bộ 10/10 truy vấn retrieval thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  Triển khai trong `CorrelationIdMiddleware` kế thừa `BaseHTTPMiddleware`. Đầu mỗi request, gọi `clear_contextvars()` để xóa context cũ tránh rò rỉ giữa các request. Kiểm tra header `x-request-id`, nếu có thì nhận lại, nếu không thì sinh mới theo định dạng `req-<8-hex>` (`f"req-{uuid.uuid4().hex[:8]}"`). Bind ID vào structlog qua `bind_contextvars(correlation_id=correlation_id)` và lưu vào `request.state.correlation_id`. Sau khi xử lý request, trả lại ID và thời gian xử lý qua header `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:**
  Toàn bộ log API đều được làm giàu với: `correlation_id`, `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model`, `env`, `service="api"`, `ts` (ISO timestamp UTC), `level`. Đối với log `response_sent` bổ sung: `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, và `payload`.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  Đăng ký processor `scrub_event` trong chuỗi `structlog.configure()` ngay trước `JsonlFileProcessor` và `JSONRenderer`. Hàm `scrub_event` duyệt đệ quy qua toàn bộ string / dictionary trong log event, đối chiếu bộ regex trong `PII_PATTERNS` (email, số điện thoại VN, CCCD 12 số, thẻ tín dụng 16 số) và thay thế bằng nhãn `[REDACTED_<NAME>]`. Nhờ đó dữ liệu nhạy cảm được che trước khi render JSON hoặc ghi vào file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:**
  Chạy `python scripts/validate_logs.py` kiểm tra toàn bộ file log thực tế: đạt 100/100, 0 trường thiếu, 0 rò rỉ PII và trích xuất đủ 10 unique correlation IDs. Bộ unit tests `test_pii.py` và `test_validate_logs.py` đều pass.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  Trong file `.env`, cấu hình `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` thuộc project cá nhân `day13-k4-l3a-2A202602698`. Mọi trace gửi lên đều mang metadata `user_id_hash`, `session_id`, `tags: ["lab", feature, model]` và `correlation_id` khớp với log local.
- **Cấu trúc root/retrieval/generation observations:**
  Hàm `LabAgent.run` đóng vai trò root observation (`@observe(name="lab-agent-run", as_type="agent")`). Bên trong chứa 2 child observations:
  1. `_retrieve_docs`: dạng `retriever` (`@observe(name="retrieval", as_type="retriever")`) đo thời gian tra cứu context và bắt lỗi vector store.
  2. `_generate_response`: dạng `generation` (`@observe(name="llm-generate", as_type="generation")`) bọc `FakeLLM.generate`, cập nhật `model`, `usage_details` (input, output, total tokens), `cost_details` (USD) và `prompt` qua `update_current_generation`.
- **Cách nối trace với log:**
  Trong root span của agent, `correlation_id` từ middleware được truyền vào `propagate_attributes(metadata={"correlation_id": correlation_id, ...})`. Nhờ đó, từ một log line bất thường ta tra cứu bằng `correlation_id` là tìm được đúng trace trên Langfuse.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (labels: `baseline`, `production`)
- **Version/label candidate:** Version 2 (label: `candidate`)
- **Trace ID của mỗi version:**
  - Trace baseline (v1): Ghi nhận `prompt_name=day13-chat`, `prompt_label=baseline`, `prompt_version=1`
  - Trace candidate (v2): Ghi nhận `prompt_name=day13-chat`, `prompt_label=candidate`, `prompt_version=2`
- **Cách promote và rollback `production`:**
  - Promote: Trong Langfuse UI, chuyển nhãn `production` sang Version 2 để ứng dụng tự động load bản mới.
  - Rollback: Khi phát hiện sự cố, chuyển nhãn `production` quay lại Version 1 trên giao diện Langfuse mà không cần restart hay redeploy ứng dụng.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  Được triển khai theo contract `config/dashboard.yaml` tại `/dashboard`:
  1. `latency`: Latency percentiles (P50, P95, P99) và TTFT P95 (threshold P95 <= 3000ms).
  2. `traffic`: Tổng request và requests/phút (threshold RPM >= 1).
  3. `errors`: Error rate %, breakdown lỗi và retrieval success rate % (threshold error rate <= 2%).
  4. `cost`: Tổng chi phí USD và chi phí theo phút (threshold total <= $2.5).
  5. `tokens`: Tổng lượng token in và token out (threshold <= 50,000 tokens).
  6. `quality`: Điểm chất lượng trung bình chất lượng câu trả lời (threshold >= 0.75).
- **SLO và lý do chọn:**
  SLO `fast_successful_requests`: 99.5% requests thành công và có độ trễ <= 3000ms trong 28 ngày. Ngưỡng 3000ms (~3.3x P95 baseline) bảo đảm người dùng không bị nghẽn trải nghiệm trong khi vẫn lọc được các đợt tail latency do RAG chậm hoặc LLM loop.
- **Cách tính error budget:**
  Target 99.5% tương ứng với Error Budget 0.5%. Với mỗi 1,000 requests, ngân sách cho phép tối đa 5 requests bị lỗi hoặc phản hồi vượt quá 3000ms trước khi vi phạm cam kết chất lượng.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95`: P95 latency > 3000ms duy trì 5m (Critical). Runbook: [docs/alerts.md#alert-1](../docs/alerts.md#alert-1).
  2. `HighErrorRate`: Error rate > 2% hoặc Retrieval success < 90% duy trì 3m (Critical). Runbook: [docs/alerts.md#alert-2](../docs/alerts.md#alert-2).
  3. `CostSpike`: Chi phí tích luỹ vượt $2.5/giờ duy trì 10m (Warning). Runbook: [docs/alerts.md#alert-3](../docs/alerts.md#alert-3).

## 7. Điều tra challenge

- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Khoảng thời gian điều tra:** 2026-09-29T09:23:01Z – 2026-09-29T09:23:21Z (16:23:01 – 16:23:21 GMT+7)
- **Triệu chứng từ metrics:**
  - Latency phản hồi tăng vọt bất thường: Latency P95 đạt **4,183 ms** (vượt xa ngưỡng challenge `latency_threshold_ms: 2000` và vi phạm nghiêm trọng SLO 3000ms).
  - TTFT P95 không thay đổi (**50 ms**), error rate = 0%, và retrieval success rate vẫn là 100%.
  - Tính năng bị ảnh hưởng: Toàn bộ truy vấn thuộc `feature: "monitoring"`.
- **Log line và correlation ID liên quan:**
  - Correlation ID: `req-852ec6e8` (cùng các request bị ảnh hưởng: `req-ab23406b`, `req-54f7c474`, `req-8f4d8344`, `req-9250dc7a`).
  - Log line trích xuất từ `data/logs.jsonl`:
    ```json
    {"service": "api", "latency_ms": 4183, "ttft_ms": 50, "tokens_in": 36, "tokens_out": 151, "cost_usd": 0.002373, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "env": "dev", "user_id_hash": "4570299f37e2", "session_id": "k4-l3a-challenge-s04", "model": "claude-sonnet-4-5", "feature": "monitoring", "correlation_id": "req-852ec6e8", "level": "info", "ts": "2026-09-29T09:23:07.386924Z"}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - Trace correlation ID: `req-852ec6e8`.
  - Span con gây ảnh hưởng: `retrieval` (loại `retriever`).
  - Phân tích waterfall: Span con `retrieval` tiêu tốn > 2,500 ms (chiếm > 60% tổng thời gian request), trong khi span con `llm-generate` chỉ tốn ~150 ms và TTFT token đầu tiên là 50 ms.
- **Root cause:**
  - Sự cố chậm trễ tại tầng Retrieval / Vector database (mô phỏng bởi sự cố `rag_slow` gây sleep 2.5s khi tra cứu tài liệu trong corpus `monitoring`).
- **Fix action:**
  - Tắt sự cố bằng lệnh `python scripts/inject_incident.py --disable`.
  - Trong môi trường production: Scale-out cụm vector database (tăng replica/pod), tối ưu cấu hình index vector (efSearch / HNSW), và bổ sung tầng semantic caching (Redis) cho các embedding phổ biến.
- **Preventive measure:**
  - Thiết lập timeout nghiêm ngặt cho bước retrieval (ví dụ 800ms) kèm circuit breaker: nếu vector search quá hạn thì fallback sang direct LLM generation hoặc cache cũ mà không treo toàn bộ request.
  - Cấu hình alert riêng cho retrieval latency (`retrieval_latency_p95 > 1000ms`) để phát hiện suy thoái ở tầng vector database trước khi ảnh hưởng đến SLO toàn hệ thống.
  - Giám sát độ trễ riêng biệt giữa tầng Retrieval và tầng Generation trên dashboard.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  Xử lý che PII (PII Scrubbing) ở cấp độ Processor của structlog đệ quy thay vì xử lý thủ công ở từng log call. Quyết định này đảm bảo tính nhất quán (centralized), không bỏ sót trường hợp developer quên che PII khi thêm log mới, và loại bỏ hoàn toàn nguy cơ ghi log thô chứa thông tin nhạy cảm xuống disk.
- **Một lỗi/blocker đã gặp:**
  Nguy cơ rò rỉ contextvars giữa các requests đồng thời trong kiến trúc bất đồng bộ (async ASGI) và file log cũ làm validator bị trừ điểm.
- **Cách tìm nguyên nhân và xử lý:**
  Gọi `clear_contextvars()` ngay ở đầu `CorrelationIdMiddleware.dispatch` trước khi nhận request mới để làm sạch context thread-local / async task. Đồng thời sao lưu và tạo mới `data/logs.jsonl` sau giai đoạn baseline để việc kiểm chứng phản ánh chính xác mã nguồn mới.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics (Triệu chứng)**: Giúp phát hiện vấn đề tổng quan (ví dụ: Latency P95 tăng vọt, Error rate vượt ngưỡng) và khoanh vùng khoảng thời gian xảy ra sự cố.
  - **Logs (Xác định request)**: Từ khoảng thời gian của metrics, truy vấn file logs để tìm các dòng log lỗi/chậm (`request_failed`, `response_sent`) và trích xuất `correlation_id` của request bị ảnh hưởng.
  - **Traces (Nguyên nhân gốc)**: Lấy `correlation_id` tra cứu trace trên Langfuse để mở waterfall view, phân tích cây quan hệ cha-con và thời gian thực thi của từng span (retrieval vs LLM generate) để chỉ ra chính xác span gây lỗi.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  LLM là hệ thống phi tất định và tính phí theo token tiêu thụ. Quản lý prompt versioning cho phép kiểm soát chặt chẽ các thay đổi prompt độc lập với mã nguồn, đo lường được tác động về chi phí/độ trễ trước và sau thay đổi, và cho phép rollback tức thì (zero-downtime) về version trước khi prompt mới làm tăng chi phí hoặc giảm chất lượng phản hồi.
- **Điều quan trọng nhất đã học:**
  Kỹ năng xây dựng hệ thống khả năng quan sát toàn diện (full-stack observability) cho ứng dụng GenAI/LLM theo chuẩn công nghiệp, hiểu rõ cách kết nối chuỗi bằng chứng Metrics → Logs → Traces để giải quyết sự cố sản xuất nhanh chóng và chính xác.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  Không có; toàn bộ các checkpoint CP0 đến CP4 và challenge incident K4-L3A đã được thực hiện và kiểm chứng hoàn chỉnh.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
