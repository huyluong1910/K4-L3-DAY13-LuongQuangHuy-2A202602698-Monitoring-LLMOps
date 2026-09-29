# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: HighLatencyP95
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: `fast_successful_requests` (SLO 99.5% requests có latency <= 3000ms trên cửa sổ 28 ngày)
- Điều kiện và thời gian duy trì: Latency P95 > 3000ms duy trì liên tục trong 5 phút.
- Ảnh hưởng tới người dùng: Người dùng cảm nhận hệ thống phản hồi rất chậm, nguy cơ timeout trên giao diện client.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra dashboard panel **Latency** để xác định P50 và TTFT có bị tăng đồng loạt không, hay chỉ P95/P99 tăng vọt.
  2. Lọc `data/logs.jsonl` tìm các log `response_sent` có `latency_ms > 3000` để lấy `correlation_id`.
  3. Mở Langfuse trace bằng `correlation_id` đó để soi waterfall: kiểm tra span `retrieval` (vector database/RAG) hay span `llm-generate` đang chiếm phần lớn thời gian.
- Mitigation tạm thời: Bật cache câu trả lời hoặc giảm số lượng top-k document trong RAG; nếu retrieval backend nghẽn, tạm chuyển sang chế độ direct answer hoặc degraded mode.
- Owner: oncall-llmops

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- Duration: 3m
- Kênh thông báo: Slack (#alerts-llmops)
- SLI/SLO liên quan: Error rate guardrail (< 2%), Retrieval success rate guardrail (>= 90%)
- Điều kiện và thời gian duy trì: Error rate > 2% hoặc Retrieval success rate < 90% duy trì liên tục trong 3 phút.
- Ảnh hưởng tới người dùng: Nhiều request trả về mã lỗi HTTP 500 hoặc câu trả lời fallback không có thông tin chính xác.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel **Errors** trên dashboard để xem tỷ lệ lỗi và breakdown theo `error_type` (ví dụ `RuntimeError: Vector store timeout`).
  2. Tra cứu log `request_failed` gần nhất trong `data/logs.jsonl` để lấy `correlation_id` và `payload.detail`.
  3. Mở trace trên Langfuse để xác định span bị lỗi (thường là span retrieval hoặc provider API).
- Mitigation tạm thời: Bật fallback vector store hoặc bypass bước retrieval khi phát hiện vector store timeout; thông báo tình trạng dịch vụ qua status page nếu sự cố do upstream provider.
- Owner: oncall-llmops

## Alert 3

- Tên: CostSpike
- Severity: warning
- Duration: 10m
- Kênh thông báo: Slack (#finops-llm)
- SLI/SLO liên quan: Cost guardrail (< 2.5 USD / ngày hoặc 2.5 USD / giờ tải cao)
- Điều kiện và thời gian duy trì: Tổng chi phí tích luỹ trong 1 giờ vượt quá 2.5 USD liên tục trong 10 phút.
- Ảnh hưởng tới người dùng: Không ảnh hưởng trực tiếp đến người dùng cuối nhưng đe dọa ngân sách vận hành của doanh nghiệp.
- Ba bước kiểm tra đầu tiên:
  1. Kiểm tra panel **Cost** và **Tokens** trên dashboard để xác định chi phí tăng do đột biến traffic (Request/min tăng) hay do mỗi request sinh quá nhiều token (`tokens_out` tăng vọt).
  2. Lọc `data/logs.jsonl` các dòng `response_sent` có `tokens_out > 500` hoặc `cost_usd` cao bất thường.
  3. Mở Langfuse trace để kiểm tra prompt version nào đang chạy và mô hình có bị lặp từ (infinite loop) hoặc verbose quá mức không.
- Mitigation tạm thời: Giảm `max_tokens` của LLM config; rollback prompt version nếu nguyên nhân do prompt mới; áp dụng rate-limit người dùng hoặc feature tiêu tốn token bất thường.
- Owner: finops-team

