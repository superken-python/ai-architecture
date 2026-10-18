# LLM-05 · Trung cấp · Viết harness agent bằng LangChain, tương đương Agno, rồi cải tiến theo Claude Code

**Kỹ năng:** [LLM-05 Tool calling và điều phối workflow/agent](../../docs/02-skill-map/generated/mang/llm.md#llm-05) · **Mức:** Trung cấp (phần cải tiến chạm mức Nâng cao)
**Thời lượng:** ~3 giờ · **Nhóm phụ thuộc:** môi trường riêng qua `uv run --with` (không thêm vào lockfile chung) · **Chi phí API ước tính:** 0 USD (model kịch bản); `eval_golden.py` với model thật < 0,1 USD

Tài liệu giải thích đầy đủ, có toàn bộ code: [docs/agent-radar/02-harness-agno-sang-langchain.md](../../docs/agent-radar/02-harness-agno-sang-langchain.md).

## Mục tiêu

Sau lab này bạn làm được: dựng một agent LangChain có lịch sử theo số run, memory dài hạn theo user, tool chạy ở
client có tạm dừng/chạy tiếp, người duyệt bước ghi và trần số bước — **chứng minh bằng test** rằng nó hành xử như
harness của Agno — rồi thêm các lớp kiểm soát kiểu Claude Code (file luật, đọc trước khi ghi, kiểm chứng sau khi
ghi, nhắc trạng thái, quyền, subagent, quản lý ngữ cảnh) và đo bằng bộ đo vàng.

## Dữ liệu

Ba khách hàng giả trong `harness/data.py`. Không có dữ liệu thật, không cần tải gì.

## Cài đặt

Phiên bản đã chạy: `langchain` 1.4.6, `langgraph` 1.2.16, `langgraph-checkpoint-sqlite` 3.1.2, `langchain-openai` 1.7.2;
mục 6 thêm `langchain-mcp-adapters` 0.3.2, `mcp` 1.30.0, `numpy` 2.3.4. Python 3.13. Từ thư mục gốc repo:

```bash
LC='--with langchain==1.4.6 --with langgraph==1.2.16 --with langgraph-checkpoint-sqlite==3.1.2 --with langchain-openai==1.7.2
    --with langchain-mcp-adapters==0.3.2 --with mcp==1.30.0 --with numpy==2.3.4'
uv run --no-project --python 3.13 $LC --with pytest python -m pytest labs/llm-05-trung-cap-harness-langchain
cd labs/llm-05-trung-cap-harness-langchain
uv run --no-project --python 3.13 $LC python demo.py             # harness tương đương Agno
uv run --no-project --python 3.13 $LC python demo.py --improved  # thêm các lớp cải tiến
OPENAI_API_KEY=... uv run --no-project --python 3.13 $LC python eval_golden.py   # model thật
```

## Các bước

1. Đọc mục 1–3 của tài liệu: harness là gì, Agno chạy một run ra sao, ánh xạ sang LangChain.
2. Chạy `demo.py`, đối chiếu đầu ra với bảng 5 run (tài liệu mục 2.4).
3. Đọc lần lượt `harness/model.py` → `tools.py` → `instructions.py` → `history.py` → `memory.py` → `agent.py`; với
   mỗi file, tìm test tương ứng trong `tests/test_parity.py`.
4. Đổi `num_history_runs`, `limit_exit` trong test rồi xem test nào đỏ và vì sao.
5. Đọc `harness/improved.py` và `tests/test_improved.py`; chạy `demo.py --improved`, tìm `<system-reminder>`.
6. Có API key: chạy `eval_golden.py`, sửa docstring một tool, chạy lại, so điểm.
7. Đọc mục 6 của tài liệu (phần còn lại của Lab 01 Agno): `harness/structured.py` → `state.py` → `guards.py` →
   `knowledge.py` → `mcp_tools.py` → `team.py` → `workflow.py`, mỗi file với test trong `tests/test_agno_mapping.py`
   và `tests/test_workflow.py`; so cột "khác biệt đã đo" với hành vi bạn thấy ở lab Agno.

## Kiểm tra kết quả

- [ ] 72 test xanh: 47 test hành vi (`test_parity.py`, `test_improved.py`, `test_agno_mapping.py`,
      `test_workflow.py`) + 25 test đồng bộ tài liệu–code (`test_doc_sync.py`; sửa code xong chạy `python sync_doc.py`).
- [ ] Giải thích được vì sao post-hook của Agno để lại câu vi phạm trong `content` còn `@after_agent` thì không (mục 6.3).
- [ ] Giải thích được vì sao `exit_behavior="continue"` cho model 9 lượt còn `"end"` chỉ 3 lượt.
- [ ] Chỉ ra trong `demo.py` run nào mất run 1 khỏi lịch sử, và cái gì của run 1 vẫn còn.
- [ ] Với model thật: `eval_golden.py` in số ca đạt, token vào/ra và chi phí.

## Câu hỏi mở rộng

- Ghép harness này vào một bước của workflow `StateGraph` ([Lab 03 LangGraph](../../docs/self-practices/guide_03_langgraph.md)).
- (Để sau) Viết endpoint AG-UI cho agent này để thay AgentOS trong CMB-10 (tài liệu mục 7).
- Đặt harness của mục 4 vào node `write` của workflow mục 6.7 (bước cần tự chọn tool) và giữ người duyệt ở node `review`.
- Đo độ trễ thêm vào của `UserMemoryMiddleware` (ghi tuần tự ở `after_agent`) so với Agno (ghi song song); chuyển
  sang chạy nền mà vẫn bảo đảm ghi xong trước khi trả lời.
- Thêm `LLMToolSelectorMiddleware` khi số tool > 15 và đo bằng bộ đo vàng.

## Cảnh báo đã biết

Khi run dừng ở `interrupt()` với `context=AgentContext(...)`, pydantic in `UserWarning` về serializer của trường
`context`. Không ảnh hưởng kết quả.
