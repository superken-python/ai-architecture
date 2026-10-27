# 02 · Mapping kết quả Semgrep ↔ IPA, export IPA knowledge base và cập nhật liên tục

Ngày: 2026-10-27 · Đọc trước: [01 · Nghiên cứu IPA, CWE, Semgrep](01-nghien-cuu-ipa-cwe-semgrep.md) (có giải thích nhãn **[đã kiểm chứng]** / **[tìm kiếm web]** / **[chưa xác minh]** và lý do một số trang IPA/MITRE/Semgrep chưa đọc trực tiếp được).

## 1 · Tóm tắt

1. **Cầu nối là CWE.** Mỗi rule Semgrep gắn sẵn mã CWE trong metadata; IPA phân loại lỗ hổng theo CWE. Chuỗi mapping: `finding → rule → CWE → mục IPA → đối sách IPA`.
2. **Bảng IPA↔CWE phải tự biên soạn rồi kiểm duyệt.** Mình chưa thấy nguồn nào xuất sẵn bảng này dưới dạng dữ liệu (mới chỉ tìm kiếm web, chưa đọc được trang IPA). Bản seed trong `templates/` ghi theo trí nhớ, mọi dòng đều gắn `seed_unverified`.
3. **11 mục IPA chỉ phủ khoảng 1/4 những gì Semgrep gắn CWE.** Đo trên 1.662 cặp rule–CWE: 22,6% khớp trực tiếp, 2,2% khớp qua cây CWE, **75,2% không thuộc mục nào** (hard-code credential, mật mã, SSRF, deserialization, XXE...). Vì vậy bắt buộc có trạng thái `OUT_OF_IPA_SCOPE`, không được bỏ những finding này.
4. **Tag CWE của Semgrep có chỗ sai** (ví dụ 2 biến thể `tainted-sql-string` của Python bị gắn CWE-915/704 thay vì CWE-89) → cần bảng `semgrep_cwe_override` có người duyệt.
5. **Cập nhật liên tục** = job định kỳ phát hiện thay đổi ở từng nguồn → chạy ETL → sinh diff → **mở PR cho người duyệt** → merge → dựng lại DB. Nội dung lấy từ IPA không bao giờ tự động merge.
6. **Đã chạy thử thật** (SQLite, dữ liệu mẫu trong repo, scan thật): xem mục 5. Các đoạn code ở mục 8 đã được chạy trước khi đưa vào đây.

---

## 2 · Mô hình liên hệ

```
 Semgrep scan (JSON/SARIF)        Semgrep rule catalog            CWE catalog (MITRE)         IPA knowledge base
 ─────────────────────────        ───────────────────────         ───────────────────         ──────────────────────────
 finding                          semgrep_rule_cwe                cwe_catalog                 ipa_item  (11 mục)
  check_id ────(hậu tố)────────►   (rule_file, rule_id)             cwe_id  ◄── cwe_relation    ipa_countermeasure
  path, line, severity            cwe_id ──────────────────────►  (cha–con, view 1000)        (gốc rễ / bảo hiểm)
                                   ▲                                   ▲                            ▲
                                   │ semgrep_cwe_override              └────── ipa_cwe_map ─────────┘
                                   │ (replace / add / ignore,           (relation, confidence,
                                   │  có người duyệt)                    verification_status)
```

Kết quả cuối: mỗi dòng báo cáo = `(file, dòng, mục IPA, số rule báo, CWE, kiểu khớp)` kèm danh sách đối sách IPA; phần còn lại xuất ra `OUT_OF_IPA_SCOPE` hoặc `NO_CWE`.

---

## 3 · Quy tắc mapping

### 3.1 Các bước

1. **Chuẩn hóa finding.** Lấy `check_id`, `path`, `start.line`, `extra.severity` từ JSON. *Không* dựa vào `extra.metadata.cwe` của finding làm nguồn sự thật cuối: tra lại từ catalog rule để áp override (xem 3.4).
2. **Khớp finding → rule** bằng hậu tố: `check_id` kết thúc bằng `.<check_id_suffix>` (với `--config <thư mục>`, `check_id` = tiền tố đường dẫn config + thư mục chấm + rule id). Khóa duy nhất là `(rule_file, rule_id)`, vì `rule_id` đơn lẻ trùng ở 64 chỗ.
3. **Rule → CWE hiệu lực** = CWE của rule, thay bằng/bổ sung theo `semgrep_cwe_override` đã `approved`.
4. **CWE → mục IPA** qua `ipa_cwe_map` (khớp trực tiếp). Nếu CWE không có trong bảng, thử đi lên cây `ChildOf` (view 1000, tối đa 4 cấp) và gặp CWE `exact` của một mục IPA thì ghi là `ancestor` (ứng viên).
5. **Gộp trùng** theo `(file, dòng, mục IPA)`: nhiều rule cùng báo một lỗi (ví dụ 4 rule cho OS command injection ở một dòng) thành một dòng báo cáo, giữ `n_rules` để biết mức đồng thuận.
6. **Giữ phần không map được**: có CWE nhưng không thuộc mục IPA → `OUT_OF_IPA_SCOPE`; không có CWE → `NO_CWE`.

### 3.2 Kiểu khớp và cách dùng

| `match_kind` | Ý nghĩa | Độ tin cậy | Dùng làm |
|---|---|---|---|
| `exact` | CWE của finding chính là CWE của mục IPA | Cao | Kết luận, đếm vào KPI |
| `narrower` | CWE cụ thể hơn CWE chính của mục IPA (ví dụ 862 dưới 285) | Cao–trung bình | Kết luận |
| `broader` | CWE tổng quát hơn (ví dụ 77 trên 78) | Trung bình | Ứng viên, người xem mã |
| `related` | Liên quan gián tiếp (ví dụ cookie thiếu `Secure` với quản lý phiên) | Thấp | Gợi ý, **không** đếm vào KPI |
| `ancestor` | CWE là hậu duệ ≤ 4 cấp của CWE `exact`, suy ra từ cây | Thấp–trung bình | Ứng viên chờ duyệt |

Khớp theo cây thuần túy dễ ra kết quả sai nghĩa (lần thử đầu, khi cho phép đi lên mọi tổ tiên, CWE-1004 "thiếu HttpOnly" bị xếp vào nhóm access control). Vì thế `ancestor` luôn là **ứng viên**, và danh sách `related` do người chọn trong `ipa_cwe_map`.

### 3.3 Điểm cần đặc biệt chú ý

- Tránh đếm trùng: 1 lỗi thật có thể sinh 4+ finding. Báo cáo cho quản lý dùng số dòng đã gộp, không dùng số finding thô.
- `NO_CWE` thường là rule `best-practice`/`correctness` (không có CWE), ví dụ `use-timeout`; không nên coi là lỗ hổng.
- Không có finding ≠ không có lỗ hổng: ví dụ ở mục 5 có 3 lỗi cố ý không bị báo (chi tiết ở tài liệu 01, mục 3.4). Độ phủ IPA phải đo bằng bộ mã có lỗi cố ý, không suy ra từ việc scan "sạch".

### 3.4 Override CWE (`semgrep_cwe_override.csv`)

| Hành động | Tác dụng | Ví dụ thật trong bản mẫu |
|---|---|---|
| `replace` | Bỏ `cwe_id_from_rule`, thay bằng `cwe_id_override` | `python/django/.../tainted-sql-string.yaml`: 915 → 89; `python/flask/.../tainted-sql-string.yaml`: 704 → 89 (11 biến thể cùng tên ở ngôn ngữ khác đều là CWE-89) |
| `add` | Giữ CWE cũ, thêm CWE mới | `hardcoded-config.yaml` (rule `avoid_hardcoded_config_SECRET_KEY`): giữ 489, thêm 798 |
| `ignore` | Bỏ CWE này khỏi mapping | (chưa có) |

Chỉ áp override có `verification_status = 'approved'`. Hai dòng đầu là bằng chứng mạnh (so sánh với biến thể cùng tên), dòng thứ ba là nhận định cần reviewer xác nhận nên đang để `proposed`.

### 3.5 Cổng chất lượng trước khi một dòng được `verified`

| # | Kiểm tra | Bản seed hiện tại |
|---|---|---|
| Q1 | Mọi khóa ngoại tồn tại (ipa_id, cwe_id, rule) | Đạt |
| Q2 | Mỗi `ipa_item` có ≥ 1 CWE `exact` | **Chưa đạt:** IPA-WEB-04 (quản lý phiên) chỉ có `related`, cần đối chiếu bản gốc |
| Q3 | Mỗi `ipa_item` có ≥ 1 đối sách `root_cause` | **Chưa đạt:** mẫu mới có 4 dòng cho SQL injection |
| Q4 | Không CWE nào trong `ipa_cwe_map` ở trạng thái Deprecated/Obsolete trong bản CWE hiện hành | Chưa chạy (cần bản CWE mới nhất) |
| Q5 | `text_ja` là nguyên văn lấy từ tài liệu IPA, có ghi số mục/trang | Chưa có dữ liệu |

Q1–Q3 đã chạy bằng script tạm lúc dựng mẫu; Q2–Q3 không đạt là **đúng thiết kế** của bản seed và chứng tỏ cổng bắt được thiếu sót.

---

## 4 · Đo thử độ phủ

Dữ liệu: `semgrep-rules` commit `16b9e6d` (2026-10-21), 1.649 rule `security`, 1.662 cặp rule–CWE, 164 CWE; cây CWE 4.14; bảng `ipa_cwe_map` bản seed **chưa xác minh**.

| Loại | Số CWE | Số cặp rule–CWE | Tỉ lệ |
|---|---|---|---|
| Khớp trực tiếp (CWE có trong `ipa_cwe_map`, mọi `relation`) | 16 | 376 | 22,6% |
| Khớp qua cây (hậu duệ ≤ 4 cấp của CWE `exact`/`narrower`) | 14 | 37 | 2,2% |
| **Không thuộc mục nào** | **134** | **1.249** | **75,2%** |

Cách đọc đúng:

- Đây là đếm **rule**, không phải finding trên mã thật. Một codebase web điển hình dồn vào SQLi/XSS/command injection nhiều hơn, nên tỉ lệ phủ trên finding thực tế có thể cao hơn. Cần đo lại trên mã thật.
- Con số phụ thuộc bản seed; nếu IPA dùng thêm CWE khác cho mỗi mục thì phần "trực tiếp" tăng lên.
- Nhóm không phủ lớn nhất: CWE-798 (hard-coded credentials, 265 rule), 1220 (108), 327 (58), 320 (51), 94 (49), 326 (49), 918 SSRF (42), 502 deserialization (42), 319 (39), 95 (31), 611 XXE (29).
- **Hệ quả thiết kế:** nếu mục tiêu là báo cáo "tuân thủ IPA", cần mở rộng `ipa_item` bằng các tài liệu IPA khác (cột `source_doc_id` đã hỗ trợ nhiều tài liệu) hoặc thêm một phân loại dự phòng cho phần ngoài 11 mục.

---

## 5 · Ví dụ end-to-end (chạy thật)

Đầu vào: file Flask mẫu có chủ ý chứa lỗi, quét bằng `semgrep-rules/python` (371 rule), cho **20 finding**. Nạp đúng các CSV trong `templates/` vào SQLite và chạy SQL ở mục 8.

**Báo cáo theo IPA** (4 dòng, từ 9 finding thô khớp được; sau khi áp override còn 11 finding thô nhưng vẫn 4 dòng):

| Dòng | Mục IPA | Số rule báo | CWE | Khớp |
|---|---|---|---|---|
| 16 | IPA-WEB-01 SQL Injection | 1 | 89 | exact |
| 19 | IPA-WEB-01 SQL Injection | 2 → **4** sau override | 89 | exact |
| 26 | IPA-WEB-02 OS Command Injection | 4 | 78 | exact |
| 31 | IPA-WEB-05 Cross-Site Scripting | 2 | 79 | exact |

Ở dòng 19, hai rule `tainted-sql-string` (Django, Flask) vốn bị gắn CWE-915/704 nên **không** được tính là SQL injection; chỉ khi override `OV-0001`/`OV-0002` được duyệt mới vào đúng mục.

**Phần không map được vào IPA** (sau override, 9 dòng, 6 vị trí khác nhau):

| Dòng | Nội dung | CWE | Trạng thái |
|---|---|---|---|
| 11 | `SECRET_KEY` hard-code | 489 (+798 nếu duyệt OV-0003) | OUT_OF_IPA_SCOPE |
| 32 | `render_template_string` | 96 | OUT_OF_IPA_SCOPE |
| 42 | open redirect | 601 | OUT_OF_IPA_SCOPE |
| 46 | băm MD5 | 327 | OUT_OF_IPA_SCOPE |
| 54 | `verify=False` | 295 | OUT_OF_IPA_SCOPE |
| 54 | `use-raise-for-status`, `use-timeout` | (không có) | NO_CWE |
| 58 | bind `0.0.0.0`, `debug=True` | 668, 489 | OUT_OF_IPA_SCOPE |

Kết quả: **4 trên 10 vị trí có cảnh báo thuộc 11 mục IPA**. Open redirect (CWE-601) là ứng viên hợp lý để bổ sung sau khi đối chiếu IPA; `render_template_string` (CWE-96, nhóm injection vào template) cần người đánh giá xem có thuộc XSS (IPA-WEB-05) không.

---

## 6 · Export IPA knowledge base

Không có thao tác "export" một chạm: phần cốt lõi của IPA là tài liệu văn bản. Đề xuất ba lớp, mỗi lớp một cách lấy:

| Lớp | Nội dung | Nguồn | Cách lấy | Máy đọc được? | Ai duyệt |
|---|---|---|---|---|---|
| **L1 · IPA curated** | 11 mục, đối sách gốc rễ/bảo hiểm, mã CWE mà IPA nêu | PDF/HTML "安全なウェブサイトの作り方" | Tải bản hiện hành → trích văn bản → người điền `ipa_item`, `ipa_countermeasure`, `ipa_cwe_map` | Không (chưa thấy bản dữ liệu) **[chưa xác minh]** | Chuyên gia bảo mật + người đọc được tiếng Nhật |
| **L2 · CWE catalog** | Weakness, Category, quan hệ cha–con | MITRE: XML, CSV theo view, REST API | Script `cwe_xml_to_csv.py` (mục 8.1) | Có | Tự động, kiểm tra diff |
| **L2b · Tên CWE tiếng Nhật** | Cột `name_ja` | Trang CWE tiếng Nhật của IPA / JVN iPedia | Chưa xác định định dạng. Nếu không có file: để trống, hoặc dịch và gắn nhãn rõ là dịch | Chưa rõ | Người đọc tiếng Nhật |
| **L3 · JVN iPedia (tùy chọn)** | Tần suất CWE trong lỗ hổng thực tế ở Nhật | MyJVN API / feed | Dùng để xếp hạng ưu tiên cho phần `OUT_OF_IPA_SCOPE`: CWE nào IPA/JVN thấy nhiều thì nên có mục | Có **[chưa xác minh]** | Tự động |

Quy trình dựng L1 (làm một lần, rồi chỉ cập nhật khi IPA ra bản mới):

1. Tải PDF hiện hành từ trang IPA (cần host `www.ipa.go.jp` được phép). Ghi phiên bản/ngày vào `source_version.csv`.
2. Chốt danh sách mục: tên tiếng Nhật, số mục, bản số mấy (cột `edition`, `section_no`) vào `ipa_item.csv`.
3. Mỗi đối sách có đánh số trong tài liệu thành một dòng `ipa_countermeasure.csv`: `text_ja` nguyên văn, `measure_type` = `root_cause` (根本的解決) hoặc `defense_in_depth` (保険的対策).
4. Mã CWE do chính IPA nêu → `ipa_cwe_map` với `source_type = ipa_official`. CWE do mình thêm → `curated`, mức tin cậy thấp hơn.
5. Chạy cổng Q1–Q5 (mục 3.5), đổi `verification_status` sang `verified` kèm `verified_by`, `verified_at`.

---

## 7 · Template CSV để import

Tám file trong [`../templates/`](../templates/), đã có dữ liệu mẫu và đã nạp thử thành công vào SQLite (tên bảng = tên file). Cột `verification_status` có mặt ở các bảng chứa tri thức do người biên soạn.

| File | Mục đích | Khóa chính | Khóa ngoại | Nguồn dữ liệu | Dòng mẫu |
|---|---|---|---|---|---|
| [`ipa_item.csv`](../templates/ipa_item.csv) | Các mục IPA (hiện 11 mục web) | `ipa_id` | | IPA, nhập tay | 11 (seed) |
| [`ipa_countermeasure.csv`](../templates/ipa_countermeasure.csv) | Đối sách gốc rễ / bảo hiểm của từng mục | `measure_id` | `ipa_id` → `ipa_item` | IPA, nhập tay | 4 (SQLi) |
| [`cwe_catalog.csv`](../templates/cwe_catalog.csv) | Danh mục CWE | `cwe_id` | | MITRE XML, tự động | 57 (mẫu) |
| [`cwe_relation.csv`](../templates/cwe_relation.csv) | Quan hệ cha–con CWE | (`cwe_id`, `related_cwe_id`, `nature`, `view_id`) | cả hai cột → `cwe_catalog` | MITRE XML, tự động | 59 (mẫu) |
| [`ipa_cwe_map.csv`](../templates/ipa_cwe_map.csv) | **Mapping IPA ↔ CWE** | `map_id` | `ipa_id`, `cwe_id` | Biên soạn + kiểm duyệt | 18 (seed) |
| [`semgrep_rule_cwe.csv`](../templates/semgrep_rule_cwe.csv) | Catalog rule Semgrep và CWE của chúng | (`rule_file`, `rule_id`, `cwe_id`) | `cwe_id` → `cwe_catalog` | `semgrep-rules`, tự động | 18 (mẫu); bản đủ 1.662 |
| [`semgrep_cwe_override.csv`](../templates/semgrep_cwe_override.csv) | Sửa CWE sai/thiếu của rule | `override_id` | (`rule_file`, `rule_id`) → `semgrep_rule_cwe` | Biên soạn + duyệt | 3 (đề xuất) |
| [`source_version.csv`](../templates/source_version.csv) | Phiên bản/hash từng nguồn, phục vụ phát hiện thay đổi | `source_id` | | Tự động | 6 |

Thứ tự nạp: `cwe_catalog` → `cwe_relation` → `ipa_item` → `ipa_countermeasure` → `ipa_cwe_map` → `semgrep_rule_cwe` → `semgrep_cwe_override` → `source_version`.

### Quy ước định dạng (để import không bị lỗi vặt)

| Quy ước | Chi tiết |
|---|---|
| Mã hóa | UTF-8, xuống dòng LF, dòng đầu là tiêu đề. Loader nên đọc `utf-8-sig` vì Excel thêm BOM khi lưu "CSV UTF-8" |
| Dấu phân cách | Dấu phẩy. Ô có dấu phẩy, nháy kép hoặc xuống dòng phải bọc trong `"..."` (lỗi quote từng xảy ra khi dựng mẫu: một ô tiếng Anh có dấu phẩy làm lệch cột) |
| Ô rỗng | NULL |
| Danh sách trong một ô | Ngăn bằng `|` (ví dụ `owasp_tags`, `technology`) |
| `cwe_id` | Số nguyên, **không** tiền tố `CWE-` (khớp định dạng CSV của MITRE) |
| Ngày | ISO 8601 (`2026-10-27`) |
| Tiếng Nhật | Giữ nguyên, không chuyển sang romaji. Mở bằng Excel thì dùng Data → From Text/CSV, chọn UTF-8 |

### Từ vựng cố định

| Cột | Giá trị |
|---|---|
| `verification_status` | `seed_unverified` → `proposed` → `verified` / `approved` → `superseded` / `rejected`. (`verified` cho bảng IPA/map, `approved` cho override) |
| `relation` (trong `ipa_cwe_map`) | `exact`, `narrower`, `broader`, `related` |
| `confidence` | `high`, `medium`, `low` |
| `source_type` | `ipa_official`, `curated`, `curated_seed`, `mitre_hierarchy`, `inferred` |
| `measure_type` | `root_cause`, `defense_in_depth` |
| `action` (trong override) | `replace`, `add`, `ignore` |
| `status` (trong `source_version`) | `ok`, `changed`, `not_fetched`, `bundled_only`, `error` |

### Lưu ý riêng về bản mẫu

- `ipa_item.csv`, `ipa_countermeasure.csv`, `ipa_cwe_map.csv` là **seed theo trí nhớ, chưa xác minh**. Không dùng cho báo cáo chính thức trước khi đối chiếu bản gốc.
- `cwe_catalog.csv` và `cwe_relation.csv` mẫu lấy từ **CWE 4.14** (gói `cwe2`), chỉ gồm các CWE seed cùng tổ tiên.
- `semgrep_rule_cwe.csv` mẫu chỉ gồm các rule bắn trong lần scan mẫu; bản đầy đủ do script ở mục 8.1 sinh ra.
- `source_version.csv`: các nguồn IPA/MITRE đang `not_fetched` vì host bị chặn trong phiên này.
- `name_ja` của CWE để trống chờ nguồn tiếng Nhật; `text_ja` của đối sách để trống chờ nguyên văn từ PDF.

---

## 8 · Import và chạy mapping (code đã chạy thử)

Tất cả chạy với Python 3.13, `pyyaml`, `sqlite3` có sẵn của Python. Dữ liệu sinh ra từ các script này (1.662 dòng `semgrep_rule_cwe`, 1.372 dòng `cwe_catalog`) là bản đầy đủ; các CSV trong `templates/` chỉ là mẫu.

### 8.1 Sinh `semgrep_rule_cwe.csv` từ repo `semgrep-rules`

<details>
<summary><code>extract_semgrep_rules.py</code> — chạy: <code>python extract_semgrep_rules.py semgrep-rules out/semgrep_rule_cwe.csv</code></summary>

```python
"""Quét thư mục semgrep-rules -> semgrep_rule_cwe.csv (1 dòng / cặp rule-CWE)."""
import csv, datetime, pathlib, re, subprocess, sys
import yaml

repo, out_csv = pathlib.Path(sys.argv[1]), sys.argv[2]
commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
today = datetime.date.today().isoformat()
join = lambda v: "|".join(v) if isinstance(v, list) else (v or "")
COLS = ("rule_file,rule_id,check_id_suffix,cwe_id,cwe_title_in_rule,languages,severity,category,confidence,"
        "likelihood,impact,subcategory,technology,owasp_tags,ruleset_repo,ruleset_commit,extracted_at").split(",")

with open(out_csv, "w", newline="", encoding="utf-8") as out:
    w = csv.writer(out, lineterminator="\n")
    w.writerow(COLS)
    for p in sorted(repo.rglob("*.yaml")):
        rel = p.relative_to(repo)
        if rel.parts[0] == "problem-based-packs" or p.name.endswith((".test.yaml", ".fixed.yaml")):
            continue                                     # bỏ gói theo chủ đề (trùng rule) và file dữ liệu test
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        for r in doc.get("rules") or []:
            m = r.get("metadata") or {}
            if not r.get("id") or m.get("category") != "security":
                continue
            cwes = m.get("cwe") or []
            for c in [cwes] if isinstance(cwes, str) else cwes:      # cwe có thể là chuỗi hoặc list
                n = re.match(r"\s*CWE-(\d+)\s*:?\s*(.*)", str(c))
                if not n:
                    continue
                w.writerow([rel, r["id"], ".".join(rel.parent.parts) + "." + r["id"], n[1], n[2],
                            join(r.get("languages")), r.get("severity"), m["category"], m.get("confidence"),
                            m.get("likelihood"), m.get("impact"), join(m.get("subcategory")),
                            join(m.get("technology")), join(m.get("owasp")),
                            "https://github.com/semgrep/semgrep-rules", commit, today])
```

Kết quả khi chạy trên commit `16b9e6d`: 1.662 dòng, 1.649 rule, 164 CWE.
</details>

### 8.2 Sinh `cwe_catalog.csv` và `cwe_relation.csv` từ XML của MITRE

<details>
<summary><code>cwe_xml_to_csv.py</code> — chạy: <code>python cwe_xml_to_csv.py cwec_v4.14.xml out/</code></summary>

```python
"""cwec_vX.Y.xml (MITRE) -> cwe_catalog.csv + cwe_relation.csv (đầy đủ Weakness + Category)."""
import csv, sys
import xml.etree.ElementTree as ET

xml_path, out_dir = sys.argv[1], sys.argv[2]
root = ET.parse(xml_path).getroot()
NS = "{http://cwe.mitre.org/cwe-7}"                  # namespace cố định của schema CWE v7
version, released = root.get("Version"), root.get("Date")

with open(f"{out_dir}/cwe_catalog.csv", "w", newline="", encoding="utf-8") as fc, \
     open(f"{out_dir}/cwe_relation.csv", "w", newline="", encoding="utf-8") as fr:
    cat, rel = csv.writer(fc, lineterminator="\n"), csv.writer(fr, lineterminator="\n")
    cat.writerow("cwe_id,kind,name_en,name_ja,abstraction,status,description_en,cwe_version,cwe_release_date,source_url".split(","))
    rel.writerow("cwe_id,related_cwe_id,nature,view_id,ordinal,cwe_version".split(","))
    for kind in ("Weakness", "Category"):
        for e in root.iter(NS + kind):
            cid, d = e.get("ID"), e.find(NS + "Description")
            cat.writerow([cid, kind, e.get("Name"), "", e.get("Abstraction") or "", e.get("Status"),
                          " ".join((d.text or "").split()) if d is not None else "",
                          version, released, f"https://cwe.mitre.org/data/definitions/{cid}.html"])
            for r in e.iter(NS + "Related_Weakness"):    # chỉ Weakness mới có quan hệ ChildOf trong view 1000
                if r.get("Nature") == "ChildOf" and r.get("View_ID") == "1000":
                    rel.writerow([cid, r.get("CWE_ID"), "ChildOf", 1000, r.get("Ordinal") or "", version])
```

Kết quả trên CWE 4.14: 963 Weakness + 409 Category (1.372 dòng), 1.076 quan hệ `ChildOf`. Khi dùng bản CWE mới hơn, kiểm tra lại namespace (`cwe-7`) trong thẻ gốc vì MITRE có thể nâng schema.
</details>

### 8.3 Nạp CSV vào SQLite và tạo báo cáo

<details>
<summary><code>load_and_map.py</code> — chạy: <code>python load_and_map.py templates scan.json mapping.sql</code></summary>

```python
import csv, json, sqlite3, pathlib, sys

tpl_dir, scan_json, sql_file = map(pathlib.Path, sys.argv[1:4])
approve = len(sys.argv) > 4 and sys.argv[4] == "approve"
db = sqlite3.connect(":memory:")
for f in sorted(tpl_dir.glob("*.csv")):          # mỗi CSV -> một bảng cùng tên, mọi cột TEXT
    with open(f, newline="", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh)
        cols = next(rd)
        db.execute(f"CREATE TABLE {f.stem} ({', '.join(c + ' TEXT' for c in cols)})")
        db.executemany(f"INSERT INTO {f.stem} VALUES ({','.join('?' * len(cols))})", rd)
db.execute("CREATE TABLE scan_finding (check_id TEXT, path TEXT, start_line INTEGER, severity TEXT)")
scan = json.load(open(scan_json, encoding="utf-8"))
db.executemany("INSERT INTO scan_finding VALUES (?,?,?,?)",
               [(r["check_id"], r["path"], r["start"]["line"], r["extra"]["severity"]) for r in scan["results"]])
if approve:                                        # chỉ để demo: coi override đề xuất là đã duyệt
    db.execute("UPDATE semgrep_cwe_override SET verification_status = 'approved'")
db.executescript(sql_file.read_text(encoding="utf-8"))
for view in ("report_ipa", "report_unmapped"):
    cur = db.execute(f"SELECT * FROM {view} ORDER BY start_line")
    print(f"== {view}")
    print(" | ".join(d[0] for d in cur.description))
    for row in cur:
        print(" | ".join(str(x) for x in row))
print("findings:", db.execute("select count(*) from scan_finding").fetchone()[0],
      "| raw (finding,ipa) rows:", db.execute("select count(*) from finding_ipa").fetchone()[0],
      "| report rows:", db.execute("select count(*) from report_ipa").fetchone()[0])
```
</details>

<details>
<summary><code>mapping.sql</code> — sáu view: rule_cwe_effective, finding_cwe, cwe_ancestor, finding_ipa, report_ipa, report_unmapped</summary>

```sql
-- 1) CWE hiệu lực của rule sau khi áp override đã duyệt
CREATE VIEW rule_cwe_effective AS
SELECT rule_file, rule_id, check_id_suffix, cwe_id, 'rule' AS cwe_source
FROM semgrep_rule_cwe r
WHERE NOT EXISTS (SELECT 1 FROM semgrep_cwe_override o
                  WHERE o.rule_file = r.rule_file AND o.rule_id = r.rule_id
                    AND o.cwe_id_from_rule = r.cwe_id
                    AND o.action IN ('replace', 'ignore') AND o.verification_status = 'approved')
UNION
SELECT DISTINCT r.rule_file, r.rule_id, r.check_id_suffix, o.cwe_id_override, 'override'
FROM semgrep_cwe_override o
JOIN semgrep_rule_cwe r ON r.rule_file = o.rule_file AND r.rule_id = o.rule_id
WHERE o.action IN ('replace', 'add') AND o.verification_status = 'approved';

-- 2) finding -> CWE (check_id của Semgrep = <tiền tố đường dẫn config>.<check_id_suffix>)
CREATE VIEW finding_cwe AS
SELECT f.path, f.start_line, f.check_id, f.severity, e.cwe_id, e.cwe_source
FROM scan_finding f
JOIN rule_cwe_effective e
  ON f.check_id = e.check_id_suffix
  OR substr(f.check_id, -length(e.check_id_suffix) - 1) = '.' || e.check_id_suffix;

-- 3) tổ tiên của CWE (ChildOf, view 1000), giới hạn 4 cấp để tránh khớp quá xa
CREATE VIEW cwe_ancestor AS
WITH RECURSIVE a(cwe_id, ancestor_id, depth) AS (
  SELECT cwe_id, related_cwe_id, 1 FROM cwe_relation WHERE nature = 'ChildOf' AND view_id = '1000'
  UNION
  SELECT a.cwe_id, r.related_cwe_id, a.depth + 1
  FROM a JOIN cwe_relation r ON r.cwe_id = a.ancestor_id AND r.nature = 'ChildOf' AND r.view_id = '1000'
  WHERE a.depth < 4)
SELECT * FROM a;

-- 4) finding -> mục IPA: khớp trực tiếp trước; chỉ khi không có mới dùng tổ tiên (xem là ứng viên)
CREATE VIEW finding_ipa AS
SELECT fc.*, m.ipa_id, m.relation AS match_kind, m.confidence
FROM finding_cwe fc JOIN ipa_cwe_map m ON m.cwe_id = fc.cwe_id
UNION ALL
SELECT fc.*, m.ipa_id, 'ancestor', m.confidence
FROM finding_cwe fc
JOIN cwe_ancestor a ON a.cwe_id = fc.cwe_id
JOIN ipa_cwe_map m ON m.cwe_id = a.ancestor_id AND m.relation = 'exact'
WHERE NOT EXISTS (SELECT 1 FROM ipa_cwe_map d WHERE d.cwe_id = fc.cwe_id);

-- 5) báo cáo: gộp theo (file, dòng, mục IPA); best_match = kiểu khớp mạnh nhất
CREATE VIEW report_ipa AS
SELECT fi.path, fi.start_line, fi.ipa_id, i.name_en AS ipa_name,
       COUNT(DISTINCT fi.check_id) AS n_rules,
       GROUP_CONCAT(DISTINCT fi.cwe_id) AS cwe_ids,
       CASE MAX(CASE fi.match_kind WHEN 'exact' THEN 5 WHEN 'narrower' THEN 4 WHEN 'broader' THEN 3
                                   WHEN 'ancestor' THEN 2 ELSE 1 END)
            WHEN 5 THEN 'exact' WHEN 4 THEN 'narrower' WHEN 3 THEN 'broader'
            WHEN 2 THEN 'ancestor' ELSE 'related' END AS best_match
FROM finding_ipa fi JOIN ipa_item i ON i.ipa_id = fi.ipa_id
GROUP BY fi.path, fi.start_line, fi.ipa_id;

-- 6) phần IPA không phủ: có CWE nhưng không có mục IPA / không có CWE
CREATE VIEW report_unmapped AS
SELECT path, start_line, check_id, GROUP_CONCAT(cwe_id) AS cwe_ids, 'OUT_OF_IPA_SCOPE' AS status
FROM finding_cwe fc
WHERE NOT EXISTS (SELECT 1 FROM finding_ipa x WHERE x.check_id = fc.check_id AND x.start_line = fc.start_line)
GROUP BY path, start_line, check_id
UNION ALL
SELECT path, start_line, check_id, '', 'NO_CWE'
FROM scan_finding f
WHERE NOT EXISTS (SELECT 1 FROM finding_cwe c WHERE c.check_id = f.check_id AND c.start_line = f.start_line);
```
</details>

**Khi chuyển sang PostgreSQL:** đổi cột số sang `INTEGER` (`cwe_id`, `related_cwe_id`, `start_line`), thêm khóa chính/ngoại như bảng ở mục 7, thay `substr(..., -n)` bằng `right(f.check_id, length(...) + 1)`, đổi `GROUP_CONCAT` thành `string_agg`. Vì dữ liệu nhỏ (khoảng 1.400 dòng CWE, 1.700 dòng rule), cách đơn giản nhất là **nạp lại toàn bộ trong một transaction** mỗi lần cập nhật, không cần UPSERT từng dòng; git giữ lịch sử.

---

## 9 · Cập nhật liên tục khi IPA (và các nguồn khác) thay đổi

### 9.1 Từng nguồn: phát hiện thay đổi thế nào

| Nguồn | Phát hiện thay đổi | Tần suất đề xuất | Khi có thay đổi |
|---|---|---|---|
| IPA "安全なウェブサイトの作り方" (HTML/PDF) | Băm (SHA-256) phần nội dung chính đã chuẩn hóa (bỏ menu, chân trang, script); phụ trợ `ETag`/`Last-Modified`; tìm chuỗi "改訂第N版" so với cột `edition` | Hằng tuần | Mở PR kèm diff văn bản; **người** cập nhật `ipa_item`/`ipa_countermeasure`/`ipa_cwe_map` |
| IPA trang CWE (JA, EN) | Như trên | Hằng tuần | Cảnh báo, người xem có đổi cách IPA dùng CWE không |
| MITRE CWE | So `version` từ REST API (hoặc `ETag` của `cwec_latest.xml.zip`) với `source_version.current_version` **[chưa xác minh endpoint]** | Hằng tuần | Tải XML → `cwe_xml_to_csv.py` → diff → chạy Q4 (CWE trong `ipa_cwe_map` còn tồn tại và không Deprecated) → PR |
| `semgrep-rules` | `git ls-remote <repo> HEAD` so với `ruleset_commit` | Hằng ngày/tuần | `git pull` → `extract_semgrep_rules.py` → diff: rule mới chưa được map, rule đổi CWE, override không còn khớp → PR |
| JVN iPedia (tùy chọn) | Feed/API **[chưa xác minh]** | Hằng quý | Cập nhật thống kê CWE phổ biến |

### 9.2 Luồng

```
 lịch (cron) ─► phát hiện thay đổi ─► tải nguồn ─► ETL ra CSV ─► kiểm tra Q1–Q5 ─► báo cáo diff
                    │ không đổi: dừng                                   │ lỗi: dừng, báo người
                    ▼                                                   ▼
                cập nhật last_checked_at                      mở PR (nhãn needs-human-review)
                                                                        │ người duyệt + merge
                                                                        ▼
                                                    dựng lại DB ─► gắn tag phiên bản dữ liệu ─► thông báo
```

Nguyên tắc:

- **Không tự merge** thay đổi từ IPA: đổi bản, đổi số mục, đổi câu chữ cần người đọc tiếng Nhật duyệt. Với bảng thuần trích xuất (`semgrep_rule_cwe`, `cwe_catalog`, `cwe_relation`) có thể cân nhắc tự merge khi mọi cổng chất lượng đạt.
- **Hash đổi chưa chắc nội dung đổi**: trang web hay đổi menu/chân trang. Hash chỉ phần nội dung chính, và vẫn để người xem diff.
- **Mapping sai âm thầm là rủi ro lớn nhất.** Mỗi lần CWE đổi (deprecate, đổi tên, đổi cha), cổng Q4 phải chặn PR nếu `ipa_cwe_map` còn trỏ vào CWE không hợp lệ.
- **Phiên bản dữ liệu:** commit `source_version.csv` cùng dữ liệu; gắn tag dạng `kb-YYYY.MM.DD`. Báo cáo scan ghi tag này để tái hiện kết quả sau này.
- **Giữ nguồn ngoài đường găng:** nếu IPA/MITRE tạm không truy cập được, job báo `error` cho nguồn đó và dùng bản dữ liệu đã commit, không làm hỏng pipeline scan.

### 9.3 Bản phác thảo GitHub Actions (**chưa chạy thử**)

Repo đã có thư mục `.github/workflows/`. Dưới đây chỉ là khung; `scripts/security_kb/refresh.py` **chưa tồn tại**, và phiên bản các action cần kiểm tra lại khi triển khai.

```yaml
name: security-kb-refresh
on:
  schedule: [{ cron: "17 3 * * 1" }]     # 03:17 UTC thứ Hai hằng tuần
  workflow_dispatch:
jobs:
  refresh:
    runs-on: ubuntu-latest
    permissions: { contents: write, pull-requests: write }
    steps:
      - uses: actions/checkout@v4
      - run: python scripts/security_kb/refresh.py      # phát hiện thay đổi -> tải -> ETL -> kiểm tra Q1-Q5 -> ghi diff
      - uses: peter-evans/create-pull-request@v6
        with:
          branch: bot/security-kb-refresh
          title: "security_scan: cập nhật nguồn IPA / CWE / Semgrep"
          body-path: projects/security_scan/reports/kb_diff.md
          labels: needs-human-review
```

Runner GitHub có Internet mở; môi trường chạy trong sandbox/cloud nội bộ thì phải mở các host: `www.ipa.go.jp`, `cwe.mitre.org`, `cwe-api.mitre.org`, `jvndb.jvn.jp`, `github.com`, `raw.githubusercontent.com`, `pypi.org`. IPA có thể giới hạn truy cập từ một số vùng/bot; thử sớm.

---

## 10 · Rủi ro, việc cần người, bước tiếp theo

**Rủi ro**

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Bản seed IPA↔CWE sai/lệch so với IPA | Cao | Không dùng chính thức trước khi đối chiếu PDF; mọi dòng `seed_unverified`; cổng Q2/Q5 |
| 11 mục IPA chỉ phủ ~1/4 rule | Cao với mục tiêu "tuân thủ IPA" | Giữ `OUT_OF_IPA_SCOPE`; mở rộng nguồn IPA; dùng JVN iPedia xếp hạng ưu tiên |
| Tag CWE của Semgrep sai | Trung bình | Bảng override có duyệt; so sánh với biến thể cùng tên |
| Rule thay đổi theo commit khiến kết quả không tái hiện | Trung bình | Ghi `ruleset_commit`, ghim commit khi chạy báo cáo chính thức |
| Giấy phép/điều khoản | Cần kiểm tra | **Semgrep Rules License v1.0** (đọc trước khi nhúng/phân phối lại rule); điều khoản sử dụng của **CWE** (file `cwe-tou` trong gói); điều khoản của **IPA** khi sao chép nguyên văn (**[chưa xác minh]**). Nếu chưa rõ, `text_ja` để trống, chỉ lưu số mục + URL + diễn giải tiếng Việt |
| Bản CWE dùng thử (4.14) cũ | Thấp–trung bình | Chỉ dùng cho dựng pipeline; tải bản mới nhất trước khi dùng thật |

**Việc cần người**

1. Cho phép host `www.ipa.go.jp`, `cwe.mitre.org`, `cwe-api.mitre.org`, `semgrep.dev`, `jvndb.jvn.jp` (hoặc gửi PDF/HTML đã tải) để đối chiếu 4 URL bạn nêu.
2. Người đọc được tiếng Nhật đối chiếu: tên 11 mục, số bản (đang giả định "改訂第7版"), mã CWE IPA thật sự dùng, nguyên văn đối sách.
3. Quyết định phạm vi: chỉ 11 mục web, hay mở rộng sang tài liệu IPA khác cho phần `OUT_OF_IPA_SCOPE`.
4. Duyệt ba override đề xuất (đặc biệt OV-0003 là nhận định, chưa phải bằng chứng).

**Bước tiếp theo đề xuất**

1. Sau khi có quyền truy cập: điền `source_version.csv`, nâng `ipa_item`/`ipa_cwe_map` lên `verified`, điền `text_ja`.
2. Tải CWE mới nhất, chạy `cwe_xml_to_csv.py`, chạy cổng Q4.
3. Chạy `extract_semgrep_rules.py` để có bản đầy đủ; quét một codebase thật có lỗi cố ý để đo độ phủ trên finding (không chỉ trên rule).
4. Viết `scripts/security_kb/refresh.py` và workflow; chạy thử không `--merge` trong 2–3 tuần để xem tần suất thay đổi thực tế.

---

## 11 · Nguồn

Đã đọc trực tiếp / chạy thật trong phiên:
- Semgrep 1.182.1 (PyPI) và repo [`semgrep/semgrep-rules`](https://github.com/semgrep/semgrep-rules) commit `16b9e6d` (file `metadata-schema.yaml.schm`, `LICENSE`, các rule YAML).
- Gói PyPI `cwe2` 3.0.0: dữ liệu CWE 4.14 (`cwec_v4.14.xml`, CSV mapping, `cwe.ABOUT`, giấy phép `cwe-tou`).

Chỉ qua kết quả WebSearch (chưa đọc trang gốc):
- IPA, trang CWE tiếng Nhật: <https://www.ipa.go.jp/security/vuln/CWE.html>
- IPA, trang CWE tiếng Anh: <https://www.ipa.go.jp/en/security/vulnerabilities/cwe.html>
- IPA, mục SCAP/CWE: <https://www.ipa.go.jp/security/vuln/scap/cwe.html>
- Báo cáo JVN iPedia theo quý của IPA, ví dụ: <https://www.ipa.go.jp/en/security/vulnerabilities/jvn/ipedia2023q2_en.html>
- Tài liệu Semgrep về trường JSON/SARIF: <https://semgrep.dev/docs/semgrep-appsec-platform/json-and-sarif>
- Tài liệu mua sắm thành phố Yokohama (bên thứ ba, có gắn CWE-601, CWE-434): <https://en.city.yokohama.lg.jp/business/nyusatsu/kakukukyoku/2019/itaku/kankyo/enekaru2019.files/0011_20190319.pdf>

URL bạn cung cấp nhưng chưa đọc được (host bị chặn): <https://www.ipa.go.jp/>, <https://www.ipa.go.jp/security/vuln/websecurity/about.html>, <https://cwe.mitre.org/about/new_to_cwe.html>, <https://semgrep.dev/>.
