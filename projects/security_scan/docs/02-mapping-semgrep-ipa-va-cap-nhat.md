# 02 · Phía công cụ: CWE trong output của Semgrep, ZAP, Trivy và cách đối chiếu với IPA

Ngày: 2026-10-27 (cập nhật lần 2: thêm Trivy và ZAP) · Đọc trước: [01 · Nghiên cứu IPA, CWE, Semgrep](01-nghien-cuu-ipa-cwe-semgrep.md) (có giải thích nhãn **[đã kiểm chứng]** / **[tìm kiếm web]** / **[chưa xác minh]** và lý do một số trang IPA/MITRE/Semgrep chưa đọc trực tiếp được).

> **Đính chính (cập nhật lần 3).** Lần trước mình xuất `exports/ipa_map_all_tools.csv` bằng cách lấy rule của Semgrep/ZAP đổ vào template. Hướng đó **sai**: IPA và NVD mới là cơ sở tri thức (KB) để các công cụ tra cứu vào, còn công cụ chỉ đưa ra khóa CWE/CVE. File đó đã bị gỡ. KB IPA + NVD, không phụ thuộc công cụ, nằm ở [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md) và thư mục [`kb/`](../kb/). Tài liệu này giờ chỉ mô tả **phía công cụ**: CWE nằm ở đâu trong output, chuẩn hóa thế nào, đo độ phủ theo rule, sửa CWE sai của rule (thư mục [`tool_side/`](../tool_side/)).

## 1 · Tóm tắt

1. **Cầu nối là CWE, với cả ba công cụ, nhưng không đồng đều.** Semgrep (SAST) gắn CWE vào *rule*; ZAP (DAST) gắn `cweid` vào mỗi *alert*; Trivy chỉ gắn `CweIDs` cho *lỗ hổng của thư viện/gói* (CVE). Cấu hình sai (misconfig), secret và license của Trivy **không có CWE**. Chuỗi mapping chung: `finding → CWE → mục IPA → đối sách IPA`.
2. **Trivy và ZAP đều là mã nguồn mở** **[đã kiểm chứng file LICENSE]**: Trivy Apache-2.0, ZAP và `zap-extensions` Apache-2.0, `trivy-checks` MIT (chi tiết ở mục 2).
3. **KB để tra cứu là IPA + NVD, không phải dữ liệu rule của công cụ** (xem đính chính ở đầu và [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md)). Các mục dưới đây mô tả phía công cụ.
4. **Bảng IPA↔CWE phải tự biên soạn rồi kiểm duyệt.** Mình chưa thấy nguồn nào xuất sẵn bảng này dưới dạng dữ liệu (mới chỉ tìm kiếm web, chưa đọc được trang IPA). Bản seed trong `templates/` ghi theo trí nhớ, mọi dòng đều gắn `seed_unverified`.
5. **11 mục IPA chỉ phủ khoảng 1/4 những gì công cụ gắn CWE.** Semgrep: 22,6% khớp trực tiếp, 2,2% khớp qua cây CWE, **75,2% không thuộc mục nào**. ZAP: 19,5% + 2,7%, **77,9% không thuộc mục nào**. Vì vậy bắt buộc có trạng thái `OUT_OF_IPA_SCOPE`, không được bỏ những finding này.
6. **ZAP bổ sung đúng chỗ Semgrep yếu:** 10/11 mục IPA có ít nhất một scan rule ZAP (kiểm tra header chống clickjacking CWE-1021, cờ cookie, token CSRF...); chỉ mục 1.8 (mail header injection) không có. Mục 1.9 (clickjacking) là ví dụ rõ: rule Semgrep duy nhất gắn CWE-1021 thực ra là rule về route của Rails (xem 4.4), còn ZAP có rule kiểm tra header đúng nghĩa.
7. **Trivy chủ yếu nằm ngoài tầm IPA:** CVE của thư viện có thể được phân loại theo CWE rồi theo mục IPA, nhưng đối sách của IPA dành cho người viết website, không phải cách vá thư viện (cách vá là nâng phiên bản). Misconfig/secret ra `NO_CWE`.
8. **Tag CWE của Semgrep có chỗ sai** (hai kiểu đã gặp: 2 biến thể `tainted-sql-string` của Python bị gắn CWE-915/704 thay vì CWE-89; rule `filter-skipping` của Rails bị gắn CWE-1021 clickjacking) → cần bảng `semgrep_cwe_override` có người duyệt.
9. **Cập nhật liên tục** = job định kỳ phát hiện thay đổi ở từng nguồn → chạy ETL → sinh diff → **mở PR cho người duyệt** → merge → dựng lại DB. Nội dung lấy từ IPA không bao giờ tự động merge.
10. **Đã chạy thật tới đâu:** Semgrep scan thật; Trivy chỉ chạy bộ chuyển đổi trên 5 file output mẫu của chính dự án Trivy (chưa chạy Trivy); ZAP chỉ kiểm thử bộ chuyển đổi trên fixture và trích CWE từ mã nguồn rule (chưa chạy ZAP). Xem mục 11 về lý do.
---

## 2 · Trivy và ZAP: mã nguồn mở không, output có CWE không

### 2.1 Trả lời nhanh

| | Semgrep | ZAP | Trivy |
|---|---|---|---|
| Loại | **SAST**: đọc mã nguồn | **DAST**: tấn công/dò website đang chạy | **SCA + container + IaC + secret + license + SBOM**: quét thành phần, cấu hình, bí mật; **không** tìm lỗi logic trong mã bạn tự viết |
| Mã nguồn mở? | Engine mở (**[chưa xác minh]** giấy phép); bộ rule theo *Semgrep Rules License v1.0* | **Có**, Apache-2.0 (repo `zaproxy`, `zap-extensions`) | **Có**, Apache-2.0 (repo `trivy`); check misconfig `trivy-checks` MIT |
| Ai duy trì | Semgrep | README ghi "ZAP by Checkmarx" | Aqua Security (ghi trong LICENSE của `trivy-checks`) |
| CWE nằm ở | metadata của rule | `cweid` của mỗi alert | `Vulnerabilities[].CweIDs` |
| Dạng | `"CWE-89: tên"`, chuỗi hoặc list | chuỗi số `"89"` | list `["CWE-79"]`, bỏ trống nếu không có |
| Không có CWE khi | rule không phải `security` | alert thông tin; giá trị `-1`/`0` | misconfig, secret, license (luôn); CVE chưa có CWE |
| Format khác | SARIF: trong `tags` | XML (lõi): `<cweid>` chỉ khi > 0; SARIF: `relationships` chỉ khi > 0 | CycloneDX: `cwes` (số nguyên); **SARIF của Trivy không có CWE** |

Tất cả ô của ZAP và Trivy lấy từ mã nguồn và dữ liệu mẫu của chính dự án **[đã kiểm chứng]**, trừ ô giấy phép engine Semgrep. Giấy phép *dữ liệu lỗ hổng* mà Trivy tải về (từ NVD, advisory của các distro...) là điều khoản riêng của từng nguồn, mình chưa đọc **[chưa xác minh]**.

### 2.2 ZAP

**Quét thế nào.** Script đóng gói sẵn trong `zaproxy/docker/` **[đã kiểm chứng]**:

| Script | Làm gì |
|---|---|
| `zap-baseline.py` | Spider mục tiêu (mặc định 1 phút) rồi chỉ chạy **passive scan**; không tấn công chủ động |
| `zap-full-scan.py` | Spider không giới hạn rồi **active scan**; có thể rất lâu |
| `zap-api-scan.py` | Quét API khai báo bằng OpenAPI/Swagger, SOAP, GraphQL |

Cả ba nhận `-J file.json` (JSON), `-x` (XML), `-r` (HTML), `-w` (Markdown). Add-on *reports* có thêm template `traditional-json`, `traditional-json-plus`, `traditional-xml`, `sarif-json`...

> **Chỉ quét hệ thống bạn sở hữu hoặc được cấp phép bằng văn bản.** Active scan gửi payload tấn công thật (SQLi, XSS, command injection...) và có thể làm hỏng dữ liệu hoặc gây gián đoạn.

**Cấu trúc JSON** (từ template `traditional-json/report.json` và fixture kiểm thử):

```json
{"@programName": "ZAP", "@version": "...", "site": [{
  "@name": "http://target", "@host": "...", "@port": "...", "@ssl": "false",
  "alerts": [{
    "pluginid": "40018", "alertRef": "40018", "alert": "SQL Injection", "name": "SQL Injection",
    "riskcode": "3", "confidence": "2", "riskdesc": "High (Medium)",
    "instances": [{"uri": "http://target/a?x=1", "method": "GET", "param": "x", "attack": "...", "evidence": "..."}],
    "count": "1", "solution": "...", "reference": "...",
    "cweid": "89", "wascid": "19", "sourceid": "1"}]}]}
```

Giá trị ví dụ ở trên chỉ minh họa cấu trúc; tên trường lấy từ template thật. `riskcode` 0–3 (Info → High). `pluginid` là mã scan rule, `alertRef` phân biệt các alert của cùng rule.

**Lấy CWE.** Mỗi scan rule khai báo trong mã Java (`getCweId()`, `getWascId()`, `getId()`); mặc định trong lõi là `cweId = -1`. Script ở mục 9.3 trích toàn bộ từ `zap-extensions` **[đã chạy]**:

| Chỉ số | Giá trị |
|---|---|
| File Java khai báo CWE | 164 (12 file không trích được số CWE) |
| Lớp scan rule (active + passive) | 148 (80 + 71 dòng rule–CWE) |
| Cặp rule–CWE có CWE > 0 | 149 |
| CWE khác nhau | 78 (3 mục là Category đã Obsolete trong CWE 4.14: 16, 264, 933) |
| Độ phủ trích | `ascanrules` 44/48 file, `pscanrules` 54/55; phần còn lại là rule thông tin không gắn CWE |

CWE phổ biến nhất trong ZAP: 20 (9 rule), 89 (8), 497 (7), 79 (6), 693 (5), 78 (4), 311 (4), 541 (4), 319 (4). Trong đó chỉ 89, 79, 78 thuộc 11 mục IPA; 20, 497, 693... là CWE quá chung hoặc về lộ thông tin nên ra `OUT_OF_IPA_SCOPE`.

**Bẫy khi dùng output ZAP:**

1. `cweid` là **chuỗi**; không có CWE thì là `-1` (mặc định trong mã) hoặc `0`. Bộ chuyển đổi coi mọi giá trị ≤ 0 hoặc rỗng là *không có CWE*. Mình chưa thấy output ZAP thật để biết giá trị chính xác khi không có CWE.
2. Vị trí là **URL + tham số**, không phải file:dòng. Muốn đối chiếu với phát hiện của Semgrep ở cùng điểm yếu cần ánh xạ endpoint ↔ mã, nằm ngoài phạm vi này. Đối chiếu chéo công cụ hiện chỉ làm được ở mức *mục IPA / CWE*, không phải vị trí.
3. Một alert có nhiều `instances`; báo cáo gộp theo (URL, mục IPA) nên 1 điểm yếu trên 1 URL chỉ 1 dòng.
4. Baseline = passive: **không có alert ≠ an toàn** (SQLi, command injection... cần active scan).
5. Không dùng được cho giai đoạn viết mã; phải có website chạy được.

### 2.3 Trivy

**Quét gì.** Các scanner khai báo trong mã **[đã kiểm chứng]**: `vuln`, `misconfig`, `secret`, `license`, `sbom`, `rbac`, `crypto`; đối tượng: image, filesystem, repo, rootfs, Kubernetes, VM, SBOM. Format xuất: `table`, `json`, `template`, `sarif`, `cyclonedx`, `spdx`, `spdx-json`, `github`, `cosign-vuln`.

**CWE đến từ đâu.** Struct `Vulnerability` trong `trivy-db` có `CweIDs []string` (`omitempty`, ví dụ `CWE-78`). Hai điểm đọc từ mã nguồn `trivy-db`:

- Với nguồn NVD, chỉ giữ giá trị **bắt đầu bằng `CWE`**, nên `NVD-CWE-Other` và `NVD-CWE-noinfo` bị loại.
- Khi nhiều nguồn cùng mô tả một CVE, `getCweIDs` lấy **nguồn đầu tiên (theo thứ tự ưu tiên) có CWE khác rỗng**.

Ví dụ một mục trong output JSON (dữ liệu thật từ golden file của Trivy):

```json
{"VulnerabilityID": "CVE-2019-11358", "PkgName": "jquery", "InstalledVersion": "3.3.9",
 "Severity": "MEDIUM", "CweIDs": ["CWE-79"]}
```

**Không có CWE.** `DetectedMisconfiguration` có `ID` (ví dụ `KSV-0001`), `Title`, `Severity`, `Resolution`... nhưng **không có trường CWE**. Metadata các check trong `trivy-checks` có `id`, `severity`, `frameworks` (CIS...), `recommended_action`; tìm "cwe" (không phân biệt hoa thường) trong toàn repo, nơi có khoảng 1.150 file rego, chỉ khớp ngẫu nhiên trong `go.sum`. Rule secret có `ID`, `Category`, `Title`, `Severity`, `Regex`; cũng không có CWE. Một công cụ bên thứ ba tìm được qua web search có gán CWE cho misconfig bằng bảng tra của riêng họ **[tìm kiếm web]**; đó không phải output của Trivy.

**Bẫy khi dùng output Trivy:**

1. **`CweIDs` có thể vắng** (`omitempty`) ngay cả với CVE: trong 81 golden file, 105/126 mục lỗ hổng có `CweIDs` (khoảng 83%); đây là dữ liệu kiểm thử của Trivy, **không** đại diện cho thực tế.
2. Một CVE có thể có **nhiều CWE**; cùng một CVE xuất hiện cho nhiều gói (ví dụ `libssl` và `libcrypto`) → gộp theo (target, gói, CVE).
3. **Kết quả đổi theo ngày** vì DB lỗ hổng cập nhật; báo cáo phải ghi phiên bản/ngày DB.
4. Phân loại CVE thư viện theo IPA chỉ là **phân loại**: ví dụ CVE `musl` CWE-787 → qua cây CWE (con của CWE-119) → IPA-WEB-10 (buffer overflow), nhưng đối sách "viết mã C an toàn" của IPA không phải cách xử lý; cách xử lý là cập nhật gói (`FixedVersion`). Báo cáo nên tách riêng nhóm này khỏi lỗi trong mã tự viết.
5. Misconfig/secret: nếu muốn đưa vào IPA phải có **bảng tra do người biên soạn** (ví dụ secret → CWE-798), đánh dấu `source_type = curated`, không coi là output của Trivy. Mặc định giữ `NO_CWE`.
6. DB mặc định tải từ `ghcr.io/aquasecurity/trivy-db` (dự phòng `mirror.gcr.io/aquasec/trivy-db`) **[đã kiểm chứng trong mã nguồn]**; môi trường quét phải truy cập được các host này.

### 2.4 Hệ quả cho thiết kế mapping

- Chuẩn hóa CWE từ ba kiểu về một kiểu: `"CWE-89: tên"` (Semgrep), `"89"` (ZAP), `"CWE-79"` (Trivy) → số nguyên `89`; bỏ `-1`, `0`, rỗng, `NVD-CWE-*`.
- Semgrep tra CWE từ catalog rule (để áp override); ZAP và Trivy lấy CWE từ chính finding.
- Một bảng `scan_finding` chung có cột `tool`; ba loại vị trí khác nhau (file:dòng, URL, `target :: gói@phiên bản`) đều đưa vào cột `path` (+ `start_line` nếu có).
- Báo cáo luôn có ba nhóm: *khớp mục IPA*, `OUT_OF_IPA_SCOPE`, `NO_CWE`, và hiển thị theo công cụ.

---

## 3 · Mô hình liên hệ

```
 Output công cụ                    Catalog rule (nếu có)            CWE (MITRE)                 IPA knowledge base
 ───────────────                   ─────────────────────            ───────────                 ──────────────────────────
 Semgrep: finding ──(hậu tố)────►  semgrep_rule_cwe ─┐
   check_id, path, line            + semgrep_cwe_override (duyệt)│                              ipa_item  (11 mục)
 ZAP: alert/instance ── cweid ───────────────────────┼────────►  cwe_catalog  ◄── cwe_relation  ipa_countermeasure
   pluginid, uri                  (zap_rule_cwe: chỉ   │           (cha–con, view 1000)            ▲
 Trivy: CVE/gói ─── CweIDs ──────  để đo độ phủ)        │                  ▲                       │
   VulnerabilityID, pkg@ver                             └──────────────────┴──── ipa_cwe_map ─────┘
 Trivy misconfig / secret ─────── (không có CWE) ──────────────────────────────► NO_CWE            (relation, confidence,
                                                                                                    verification_status)
```

Kết quả cuối: mỗi dòng báo cáo = `(công cụ, vị trí, mục IPA, số check báo, CWE, kiểu khớp)` kèm danh sách đối sách IPA; phần còn lại xuất ra `OUT_OF_IPA_SCOPE` hoặc `NO_CWE`.

---

## 4 · Quy tắc mapping

### 4.1 Các bước

1. **Chuẩn hóa finding** về `scan_finding(tool, check_id, path, start_line, severity)` theo bảng ở mục 9.4.
2. **Lấy CWE.**
   - *Semgrep:* khớp finding → rule bằng hậu tố: `check_id` kết thúc bằng `.<check_id_suffix>` (với `--config <thư mục>`, `check_id` = tiền tố đường dẫn config + thư mục chấm + rule id). Khóa duy nhất là `(rule_file, rule_id)`, vì `rule_id` đơn lẻ trùng ở 64 chỗ. *Không* dựa vào `extra.metadata.cwe` của finding làm nguồn sự thật cuối; tra lại catalog để áp override.
   - *ZAP / Trivy:* lấy từ chính finding (`cweid` / `CweIDs`), chuẩn hóa về số nguyên, bỏ giá trị không hợp lệ.
3. **CWE hiệu lực của rule Semgrep** = CWE của rule, thay bằng/bổ sung theo `semgrep_cwe_override` đã `approved`.
4. **CWE → mục IPA** qua `ipa_cwe_map` (khớp trực tiếp). Nếu CWE không có trong bảng, thử đi lên cây `ChildOf` (view 1000, tối đa 4 cấp) và gặp CWE `exact` của một mục IPA thì ghi là `ancestor` (ứng viên).
5. **Gộp trùng** theo `(công cụ, vị trí, mục IPA)`: nhiều rule Semgrep cùng báo một lỗi (ví dụ 4 rule cho OS command injection ở một dòng), nhiều instance ZAP của cùng một URL, hoặc nhiều CVE cùng một gói thành một dòng báo cáo; giữ `n_checks` để biết mức đồng thuận.
6. **Giữ phần không map được**: có CWE nhưng không thuộc mục IPA → `OUT_OF_IPA_SCOPE`; không có CWE → `NO_CWE`.

### 4.2 Kiểu khớp và cách dùng

| `match_kind` | Ý nghĩa | Độ tin cậy | Dùng làm |
|---|---|---|---|
| `exact` | CWE của finding chính là CWE của mục IPA | Cao | Kết luận, đếm vào KPI |
| `narrower` | CWE cụ thể hơn CWE chính của mục IPA (ví dụ 862 dưới 285) | Cao–trung bình | Kết luận |
| `broader` | CWE tổng quát hơn (ví dụ 77 trên 78) | Trung bình | Ứng viên, người xem mã |
| `related` | Liên quan gián tiếp (ví dụ cookie thiếu `Secure` với quản lý phiên) | Thấp | Gợi ý, **không** đếm vào KPI |
| `ancestor` | CWE là hậu duệ ≤ 4 cấp của CWE `exact`, suy ra từ cây (ví dụ 787/120 dưới 119) | Thấp–trung bình | Ứng viên chờ duyệt |

Khớp theo cây thuần túy dễ ra kết quả sai nghĩa (lần thử đầu, khi cho phép đi lên mọi tổ tiên, CWE-1004 "thiếu HttpOnly" bị xếp vào nhóm access control). Vì thế `ancestor` luôn là **ứng viên**, và danh sách `related` do người chọn trong `ipa_cwe_map`.

### 4.3 Điểm cần đặc biệt chú ý

- Tránh đếm trùng: 1 lỗi thật có thể sinh 4+ finding. Báo cáo cho quản lý dùng số dòng đã gộp, không dùng số finding thô.
- `NO_CWE` của Semgrep thường là rule `best-practice`/`correctness` (ví dụ `use-timeout`), không phải lỗ hổng. `NO_CWE` của Trivy là misconfig/secret/CVE chưa có CWE: *có thể* là rủi ro thật, chỉ là không đi qua cầu CWE.
- Không có finding ≠ không có lỗ hổng: ví dụ ở mục 6.1 có 3 lỗi cố ý không bị Semgrep báo (chi tiết ở tài liệu 01, mục 3.4); baseline của ZAP chỉ passive. Độ phủ IPA phải đo bằng bộ mã/ứng dụng có lỗi cố ý, không suy ra từ việc scan "sạch".
- Không cộng gộp finding của ba công cụ thành "số lỗi thật": chúng khác tầng (mã, ứng dụng đang chạy, thành phần) và khác đơn vị (dòng, URL, gói). Chỉ so sánh ở mức mục IPA.

### 4.4 Override CWE (`semgrep_cwe_override.csv`)

| Hành động | Tác dụng | Ví dụ thật trong bản mẫu |
|---|---|---|
| `replace` | Bỏ `cwe_id_from_rule`, thay bằng `cwe_id_override` | `python/django/.../tainted-sql-string.yaml`: 915 → 89; `python/flask/.../tainted-sql-string.yaml`: 704 → 89 (11 biến thể cùng tên ở ngôn ngữ khác đều là CWE-89) |
| `add` | Giữ CWE cũ, thêm CWE mới | `hardcoded-config.yaml` (rule `avoid_hardcoded_config_SECRET_KEY`): giữ 489, thêm 798 |
| `ignore` | Bỏ CWE này khỏi mapping | `ruby/lang/security/filter-skipping.yaml`: bỏ CWE-1021. Message và tham chiếu (Brakeman) của rule nói về route Rails có thể render view tùy ý, không liên quan clickjacking; đây cũng là rule Semgrep **duy nhất** gắn CWE-1021 nên IPA-WEB-09 trông như đã có phủ |

Chỉ áp override có `verification_status = 'approved'`. Hai dòng `replace` là bằng chứng mạnh (so sánh với biến thể cùng tên); dòng `ignore` (OV-0004) dựa trên việc đọc nội dung rule; dòng `add` (OV-0003) chỉ là nhận định. Cả bốn đang để `proposed`, tức **chưa có hiệu lực**.

**Giới hạn hiện tại:** bảng override chỉ dành cho Semgrep. ZAP và Trivy mang CWE theo từng finding nên nếu CWE của một ZAP rule hay một CVE bị coi là sai thì chưa có chỗ sửa. Hướng mở rộng: thêm cột `tool` và khóa `(tool, check_id)` (ZAP: `pluginid`; Trivy: `VulnerabilityID`). Chưa làm vì chưa có bằng chứng về một CWE sai cụ thể ở hai công cụ này.

### 4.5 Cổng chất lượng trước khi một dòng được `verified`

| # | Kiểm tra | Bản seed hiện tại |
|---|---|---|
| Q1 | Mọi khóa ngoại tồn tại (ipa_id, cwe_id, rule) | Đạt (kể cả `zap_rule_cwe`) |
| Q2 | Mỗi `ipa_item` có ≥ 1 CWE `exact` | **Chưa đạt:** IPA-WEB-04 (quản lý phiên) chỉ có `related`, cần đối chiếu bản gốc |
| Q3 | Mỗi `ipa_item` có ≥ 1 đối sách `root_cause` | **Đạt** (từ 2026-10-28): 47 đối sách nhập từ checklist Excel bản 7 của IPA, mục nào cũng có 根本的解決 |
| Q4 | Không CWE nào trong `ipa_cwe_map` ở trạng thái Deprecated/Obsolete trong bản CWE hiện hành | Chưa chạy (cần bản CWE mới nhất) |
| Q5 | `text_ja` là nguyên văn lấy từ tài liệu IPA, có ghi số mục/trang | **Đạt** (từ 2026-10-28): `text_ja` lấy thẳng từ checklist, `measure_no` là mã của IPA như `1-(i)-a` |

Q1–Q3 đã chạy bằng script tạm lúc dựng mẫu; lúc đó Q2–Q3 không đạt là **đúng thiết kế** của bản seed và chứng tỏ cổng bắt được thiếu sót. Q3 và Q5 đạt sau khi nhập checklist của IPA (2026-10-28); Q2 vẫn chưa đạt vì checklist không có mã CWE.

---

## 5 · Đo thử độ phủ

Dữ liệu: `semgrep-rules` commit `16b9e6d` (2026-10-21); `zap-extensions` commit `51e4155` (2026-10-26); cây CWE 4.14; bảng `ipa_cwe_map` bản seed **chưa xác minh**. Đơn vị đếm là **cặp (rule, CWE)**.

| Công cụ | Cặp rule–CWE | CWE khác nhau | Khớp trực tiếp (CWE có trong `ipa_cwe_map`) | Khớp qua cây (hậu duệ ≤ 4 cấp của CWE `exact`/`narrower`) | **Không thuộc mục nào** |
|---|---|---|---|---|---|
| Semgrep (1.649 rule `security`) | 1.662 | 164 | 376 (22,6%) · 16 CWE | 37 (2,2%) · 14 CWE | **1.249 (75,2%)** · 134 CWE |
| ZAP (148 lớp scan rule) | 149 | 78 | 29 (19,5%) · 11 CWE | 4 (2,7%) · 4 CWE | **116 (77,9%)** · 63 CWE |
| Trivy | không có catalog rule: CWE đi theo từng CVE trong DB | – | chưa đo được (không tải được DB); xem minh họa dưới | | |

**Từng mục IPA có bao nhiêu rule/CWE** (khớp trực tiếp hoặc qua cây; tính từ catalog rule trong `tool_side/` ghép với bảng IPA↔CWE, chưa áp override nào):

| Mục IPA | ZAP (rule) | Semgrep (rule) | Trivy (số CWE khớp) |
|---|---|---|---|
| 1.1 SQL Injection | 8 | 79 | 2 |
| 1.2 OS Command Injection | 4 | 80 | 2 |
| 1.3 Path Traversal | 1 | 28 | 19 |
| 1.4 Quản lý phiên | 3 | 25 | 4 |
| 1.5 XSS | 6 | 130 | 9 |
| 1.6 CSRF | 3 | 21 | 1 |
| 1.7 HTTP Header Injection | 1 | 4 | 2 |
| 1.8 Mail Header Injection | **0** | 2 | 1 |
| 1.9 Clickjacking | 1 | 1 (**nghi sai tag**, xem 4.4) | 1 |
| 1.10 Buffer Overflow | 3 | 6 | 22 |
| 1.11 Thiếu kiểm soát truy cập | 3 | 39 | 40 |

Một CWE có thể thuộc hai mục IPA (CWE-93 thuộc cả 1.7 và 1.8), nên tổng các cột lớn hơn số rule khác nhau.

Số rule không so sánh được về "độ mạnh": một rule ZAP active thử nhiều payload trên nhiều tham số, trong khi nhiều rule Semgrep là biến thể theo ngôn ngữ/framework. Cái đáng nói là ZAP có mặt ở hầu hết mục, kể cả những mục kiểu cấu hình runtime (clickjacking, cookie, CSRF) mà đọc mã khó thấy.

**Minh họa cho Trivy** (không phải thống kê thực tế): trong 81 golden file của Trivy có 43 CVE khác nhau; 10 không có `CweIDs`; trong 33 CVE còn lại, 2 khớp trực tiếp, 11 khớp qua cây (chủ yếu CWE-787/125 → IPA-WEB-10), 20 không thuộc mục nào. Đây là dữ liệu chọn cho kiểm thử của Trivy, không đại diện cho phân bố CWE ngoài đời.

Cách đọc đúng:

- Đây là đếm **rule**, không phải finding trên mã thật. Một codebase web điển hình dồn vào SQLi/XSS/command injection nhiều hơn, nên tỉ lệ phủ trên finding thực tế có thể cao hơn. Cần đo lại trên mã/ứng dụng thật.
- Con số phụ thuộc bản seed; nếu IPA dùng thêm CWE khác cho mỗi mục thì phần "trực tiếp" tăng lên.
- Semgrep, nhóm không phủ lớn nhất: CWE-798 (hard-coded credentials, 265 rule), 1220 (108), 327 (58), 320 (51), 94 (49), 326 (49), 918 SSRF (42), 502 deserialization (42), 319 (39), 95 (31), 611 XXE (29).
- ZAP, nhóm không phủ lớn nhất: CWE-20 (9 rule), 497 (7), 693 (5), 311 (4), 541 (4), 319 (4), 94 (3), 215 (3), 359 (3), 598 (3), 642 (3).
- **Hệ quả thiết kế:** nếu mục tiêu là báo cáo "tuân thủ IPA", cần mở rộng `ipa_item` bằng các tài liệu IPA khác (cột `source_doc_id` đã hỗ trợ nhiều tài liệu) hoặc thêm một phân loại dự phòng cho phần ngoài 11 mục.

---

## 6 · Ví dụ end-to-end (chạy thật)

### 6.1 Semgrep

Đầu vào: file Flask mẫu có chủ ý chứa lỗi, quét bằng `semgrep-rules/python` (371 rule), cho **20 finding**. Nạp đúng các CSV trong `templates/` vào SQLite và chạy SQL ở mục 9.4.

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

### 6.2 Chạy chung Semgrep + Trivy + ZAP

Chạy `load_and_map.py` (mục 9.4) với CSV mẫu trong repo. Hồi quy: kết quả Semgrep giống hệt mục 6.1.

| Công cụ | Đầu vào | Tính chất |
|---|---|---|
| Semgrep | scan thật ở mục 6.1 | Output thật |
| Trivy | 5 golden file của dự án Trivy: `npm-with-dev` (jquery), `alpine-39` (gói OS), `gomod`, `helm` (misconfig), `secrets` | **Output thật của Trivy** do dự án lưu cho kiểm thử, với DB tại thời điểm tạo file; chưa chạy Trivy trong phiên này |
| ZAP | fixture `basic-traditional-json.json` của add-on *reports* (1 alert giả: XSS, CWE-123) + một file JSON 4 alert tự viết để thử `cweid` = `89`, `1021`, `-1`, `0` | **Không phải output ZAP thật**; chỉ kiểm tra bộ chuyển đổi |

Kết quả: **58 finding thô → 30 có CWE → 16 vào mục IPA → 9 dòng báo cáo**; 14 `OUT_OF_IPA_SCOPE`, 28 `NO_CWE`.

| Công cụ | Dòng báo cáo IPA | Ghi chú |
|---|---|---|
| Semgrep | 4 | như mục 6.1 |
| Trivy | 3 | `jquery@3.3.9` (CWE-79 → IPA-WEB-05, `exact`); `musl` và `musl-utils` (CVE-2019-14697, CWE-787 → IPA-WEB-10, `ancestor` qua CWE-119) |
| ZAP | 2 | CWE-89 → IPA-WEB-01; CWE-1021 → IPA-WEB-09 (cả hai `exact`) |

Phần còn lại của Trivy (32 finding): **24 `NO_CWE`** gồm 18 misconfig Helm (`KSV-*`), 2 secret, 4 CVE không có `CweIDs` (`GMS-2022-20` ×3, `CVE-2021-38561`); **5 `OUT_OF_IPA_SCOPE`** (CWE-330, 200, 682). Của ZAP: 2 `OUT_OF_IPA_SCOPE` (alert giả CWE-123, 2 instance) và 2 `NO_CWE` (`cweid` `-1` và `0`).

Lưu ý: bản mẫu `cwe_catalog.csv`/`cwe_relation.csv` chỉ có 69 mục CWE (các CWE xuất hiện trong mẫu cùng tổ tiên của chúng). Khi chạy với catalog CWE đầy đủ (mục 9.2) sẽ có thêm các khớp `ancestor`. CWE-787 và 125 đã được thêm vào bản mẫu để minh họa nhánh này; nếu không có hàng quan hệ của một CWE trong `cwe_relation`, CWE đó không thể đi lên cây và ra `OUT_OF_IPA_SCOPE`.

---

## 7 · Export IPA knowledge base

> Đây là phác thảo ban đầu. Thiết kế đầy đủ KB **IPA + NVD** (thêm JVN iPedia của IPA, NVD, chính sách chọn CWE, file export và cách cập nhật) ở [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md).

Không có thao tác "export" một chạm: phần cốt lõi của IPA là tài liệu văn bản. Đề xuất ba lớp, mỗi lớp một cách lấy:

| Lớp | Nội dung | Nguồn | Cách lấy | Máy đọc được? | Ai duyệt |
|---|---|---|---|---|---|
| **L1 · IPA curated** | 11 mục, đối sách gốc rễ/bảo hiểm, mã CWE mà IPA nêu | PDF/HTML "安全なウェブサイトの作り方" | Tải bản hiện hành → trích văn bản → người điền `ipa_item`, `ipa_countermeasure`, `ipa_cwe_map` | Không (chưa thấy bản dữ liệu) **[chưa xác minh]** | Chuyên gia bảo mật + người đọc được tiếng Nhật |
| **L2 · CWE catalog** | Weakness, Category, quan hệ cha–con | MITRE: XML, CSV theo view, REST API | Script `cwe_xml_to_csv.py` (mục 9.2) | Có | Tự động, kiểm tra diff |
| **L2b · Tên CWE tiếng Nhật** | Cột `name_ja` | Trang CWE tiếng Nhật của IPA / JVN iPedia | Chưa xác định định dạng. Nếu không có file: để trống, hoặc dịch và gắn nhãn rõ là dịch | Chưa rõ | Người đọc tiếng Nhật |
| **L3 · JVN iPedia (tùy chọn)** | Tần suất CWE trong lỗ hổng thực tế ở Nhật | MyJVN API / feed | Dùng để xếp hạng ưu tiên cho phần `OUT_OF_IPA_SCOPE`: CWE nào IPA/JVN thấy nhiều thì nên có mục | Có **[chưa xác minh]** | Tự động |

Trivy và ZAP không cần bước export riêng: CWE đã nằm trong output. Catalog rule ZAP (`zap_rule_cwe`) chỉ phục vụ đo độ phủ và, sau này, override.

Quy trình dựng L1 (làm một lần, rồi chỉ cập nhật khi IPA ra bản mới):

1. Tải PDF hiện hành từ trang IPA (cần host `www.ipa.go.jp` được phép). Ghi phiên bản/ngày vào `source_version.csv`.
2. Chốt danh sách mục: tên tiếng Nhật, số mục, bản số mấy (cột `edition`, `section_no`) vào `ipa_item.csv`.
3. Mỗi đối sách có đánh số trong tài liệu thành một dòng `ipa_countermeasure.csv`: `text_ja` nguyên văn, `measure_type` = `root_cause` (根本的解決) hoặc `defense_in_depth` (保険的対策).
4. Mã CWE do chính IPA nêu → `ipa_cwe_map` với `source_type = ipa_official`. CWE do mình thêm → `curated`, mức tin cậy thấp hơn.
5. Chạy cổng Q1–Q5 (mục 4.5), đổi `verification_status` sang `verified` kèm `verified_by`, `verified_at`.

---

## 8 · Template CSV: nguồn IPA/CWE và phía công cụ

Sáu file nguồn IPA/CWE trong [`../templates/`](../templates/) và ba file phía công cụ trong [`../tool_side/`](../tool_side/), đã có dữ liệu mẫu và đã nạp thử thành công vào SQLite (tên bảng = tên file). Bản export KB để công cụ tra cứu nằm ở [`../kb/`](../kb/), xem [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md). Cột `verification_status` có mặt ở các bảng chứa tri thức do người biên soạn.

| File | Mục đích | Khóa chính | Khóa ngoại | Nguồn dữ liệu | Dòng mẫu |
|---|---|---|---|---|---|
| [`ipa_item.csv`](../templates/ipa_item.csv) | Các mục IPA (hiện 11 mục web) | `ipa_id` | | IPA, đối chiếu với checklist bản 7 | 11 (`verified`) |
| [`ipa_countermeasure.csv`](../templates/ipa_countermeasure.csv) | Đối sách gốc rễ / bảo hiểm của từng mục | `measure_id` | `ipa_id` → `ipa_item` | IPA, nhập từ checklist bản 7 bằng `import_ipa_checklist.py` (tài liệu 05) | 47 |
| [`cwe_catalog.csv`](../templates/cwe_catalog.csv) | Danh mục CWE | `cwe_id` | | MITRE XML, tự động | 69 (mẫu) |
| [`cwe_relation.csv`](../templates/cwe_relation.csv) | Quan hệ cha–con CWE | (`cwe_id`, `related_cwe_id`, `nature`, `view_id`) | cả hai cột → `cwe_catalog` | MITRE XML, tự động | 71 (mẫu) |
| [`ipa_cwe_map.csv`](../templates/ipa_cwe_map.csv) | **Mapping IPA ↔ CWE** | `map_id` | `ipa_id`, `cwe_id` | Biên soạn + kiểm duyệt | 18 (seed) |
| [`semgrep_rule_cwe.csv`](../tool_side/semgrep_rule_cwe.csv) | Catalog rule Semgrep và CWE của chúng | (`rule_file`, `rule_id`, `cwe_id`) | `cwe_id` → `cwe_catalog` | `semgrep-rules`, tự động | 19 (mẫu); bản đủ 1.662 |
| [`zap_rule_cwe.csv`](../tool_side/zap_rule_cwe.csv) | Catalog scan rule ZAP và CWE của chúng | (`addon`, `rule_class`, `cwe_id`) | `cwe_id` → `cwe_catalog` | `zap-extensions`, tự động | 17 (mẫu); bản đủ 168 dòng (151 dòng scan rule) |
| [`semgrep_cwe_override.csv`](../tool_side/semgrep_cwe_override.csv) | Sửa CWE sai/thiếu của rule Semgrep | `override_id` | (`rule_file`, `rule_id`) → `semgrep_rule_cwe` | Biên soạn + duyệt | 4 (đề xuất) |
| [`source_version.csv`](../templates/source_version.csv) | Phiên bản/hash từng nguồn, phục vụ phát hiện thay đổi | `source_id` | | Tự động | 15 |

Thứ tự nạp: `cwe_catalog` → `cwe_relation` → `ipa_item` → `ipa_countermeasure` → `ipa_cwe_map` → `semgrep_rule_cwe` → `zap_rule_cwe` → `semgrep_cwe_override` → `source_version`.

Kết quả scan **không** nằm trong CSV mẫu: loader (mục 9.4) tạo bảng `scan_finding` và `scan_finding_cwe` từ file JSON mỗi lần chạy.

### Đính chính: không còn file import ghép từ rule của công cụ

Bản trước có `exports/ipa_map_all_tools.csv` ghép rule của Semgrep/ZAP với mục IPA. Đó là đi ngược chiều nên đã gỡ. File để import và để công cụ tra cứu bây giờ là KB IPA + NVD: [`../kb/kb_cwe.csv`](../kb/kb_cwe.csv) (khóa CWE) và [`../kb/kb_cve.sample.csv`](../kb/kb_cve.sample.csv) (khóa CVE), mô tả ở [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md).

### Quy ước định dạng (để import không bị lỗi vặt)

| Quy ước | Chi tiết |
|---|---|
| Mã hóa | UTF-8, xuống dòng LF, dòng đầu là tiêu đề. Loader nên đọc `utf-8-sig` vì Excel thêm BOM khi lưu "CSV UTF-8" |
| Dấu phân cách | Dấu phẩy. Ô có dấu phẩy, nháy kép hoặc xuống dòng phải bọc trong `"..."` (lỗi quote từng xảy ra khi dựng mẫu: một ô tiếng Anh có dấu phẩy làm lệch cột) |
| Ô rỗng | NULL |
| Danh sách trong một ô | Ngăn bằng `|` (ví dụ `owasp_tags`, `technology`) |
| `cwe_id` | Số nguyên, **không** tiền tố `CWE-` (khớp định dạng CSV của MITRE và `cweid` của ZAP) |
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
| `rule_type` (trong `zap_rule_cwe`) | `active`, `passive`, `other` |
| `status` (trong `source_version`) | `ok`, `changed`, `not_fetched`, `bundled_only`, `error` |

### Lưu ý riêng về bản mẫu

- `ipa_item.csv` (11 mục) và `ipa_countermeasure.csv` (47 đối sách) **đã đối chiếu với checklist Excel 改訂第7版 của IPA** (2026-10-28, file do người dùng cung cấp). `ipa_cwe_map.csv` vẫn là **seed theo trí nhớ, chưa xác minh**, vì checklist không có mã CWE. Không dùng mapping IPA↔CWE cho báo cáo chính thức trước khi đối chiếu.
- `cwe_catalog.csv` và `cwe_relation.csv` mẫu lấy từ **CWE 4.14** (gói `cwe2`), chỉ gồm các CWE seed, CWE xuất hiện trong mẫu Semgrep/ZAP/Trivy và tổ tiên của chúng.
- `semgrep_rule_cwe.csv` và `zap_rule_cwe.csv` mẫu chỉ là một phần nhỏ; bản đầy đủ do các script ở mục 9 sinh ra. Với ZAP, một số dòng không có `plugin_id` là lớp trừu tượng hoặc rule khai báo ID theo cách khác, cần xem tay.
- `source_version.csv`: các nguồn IPA/MITRE và `trivy_db` đang `not_fetched` vì host bị chặn hoặc chưa thử trong phiên này.
- `name_ja` của CWE trong `cwe_catalog.csv` để trống chờ nguồn tiếng Nhật; `text_ja` của đối sách đã có (nguyên văn checklist), kèm bản dịch `text_en`/`text_vi` của mình.

---

## 9 · Import và chạy mapping (code đã chạy thử)

Tất cả chạy với Python 3.13, `pyyaml`, `sqlite3` có sẵn của Python. Dữ liệu sinh ra từ các script này (1.662 dòng `semgrep_rule_cwe`, 168 dòng `zap_rule_cwe` trong đó 151 dòng là scan rule active/passive, 1.372 dòng `cwe_catalog`) là bản đầy đủ; các CSV trong `templates/` chỉ là mẫu.

### 9.1 Sinh `semgrep_rule_cwe.csv` từ repo `semgrep-rules`

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

### 9.2 Sinh `cwe_catalog.csv` và `cwe_relation.csv` từ XML của MITRE

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

### 9.3 Sinh `zap_rule_cwe.csv` từ repo `zap-extensions`

<details>
<summary><code>extract_zap_rules.py</code> — chạy: <code>python extract_zap_rules.py zap-extensions out/zap_rule_cwe.csv</code></summary>

```python
"""Quét zap-extensions -> zap_rule_cwe.csv (1 dòng / cặp scan rule - CWE)."""
import csv, datetime, pathlib, re, subprocess, sys

repo, out_csv = pathlib.Path(sys.argv[1]), sys.argv[2]
commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
today = datetime.date.today().isoformat()
ACTIVE = re.compile(r"extends\s+(AbstractAppPlugin|AbstractAppParamPlugin|AbstractHostPlugin|AbstractPlugin|\w*ActiveScanRule|\w*ScanRule)\b|extends\s+Abstract\w*Plugin")
PASSIVE = re.compile(r"PluginPassiveScanner|PassiveScanRule|PassiveScanner")
CONST = re.compile(r"(?:static\s+final|final\s+static)\s+int\s+(\w+)\s*=\s*(-?\d+)\s*;")

def body(text, name):
    """Thân hàm `name()` đầu tiên (đến dấu } khớp)."""
    m = re.search(r"\b" + name + r"\s*\(\s*\)\s*\{", text)
    if not m:
        return ""
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i]

def ints(text, fn):
    consts = dict(CONST.findall(text))
    found = []
    for v in re.findall(r"return\s+([\w.]+)\s*;", body(text, fn)):
        v = consts.get(v.split(".")[-1], v)
        if re.fullmatch(r"-?\d+", v):
            found.append(int(v))
    return found

COLS = "addon,rule_class,rule_type,plugin_id,cwe_id,wasc_id,java_file,zap_extensions_commit,extracted_at".split(",")
n_files = n_nocwe = 0
with open(out_csv, "w", newline="", encoding="utf-8") as out:
    w = csv.writer(out, lineterminator="\n")
    w.writerow(COLS)
    for p in sorted(repo.glob("addOns/*/src/main/java/**/*.java")):
        t = p.read_text(encoding="utf-8", errors="ignore")
        if "getCweId" not in t and "setCweId" not in t:
            continue
        cls = re.search(r"^(?:public\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)", t, re.M)
        if not cls:
            continue
        n_files += 1
        rtype = "passive" if PASSIVE.search(t) else "active" if ACTIVE.search(t) else "other"
        cwes = ints(t, "getCweId") or [int(x) for x in re.findall(r"setCweId\(\s*(-?\d+)\s*\)", t)]
        pid = (ints(t, "getId") or ints(t, "getPluginId") or [""])[0]
        wasc = (ints(t, "getWascId") or [""])[0]
        if not cwes:
            n_nocwe += 1
            cwes = [""]
        for c in dict.fromkeys(cwes):
            w.writerow([p.parts[len(repo.parts) + 1], cls[1], rtype, pid, c, wasc,
                        str(p.relative_to(repo)), commit, today])
print(f"{n_files} file có getCweId/setCweId, {n_nocwe} file không trích được số CWE", file=sys.stderr)
```

Script chỉ **đọc văn bản** các file Java, không biên dịch hay chạy mã của ZAP. Kết quả trên commit `51e4155`: 164 file → 168 dòng (151 dòng là scan rule active/passive, 17 dòng thuộc lớp khác như add-on kiểm soát truy cập), 12 file không trích được số CWE. Đã đối chiếu độ phủ: `ascanrules` 44/48 file `*ScanRule.java`, `pscanrules` 54/55. Những rule còn thiếu CWE là rule thông tin (ví dụ `UserAgentScanRule`, `ModernAppDetectionScanRule`). Hạn chế: nhận diện active/passive bằng regex trên tên lớp cha; rule khai báo CWE bằng cách khác (không qua `getCweId`/`setCweId` với số cố định) sẽ bị bỏ sót.
</details>

### 9.4 Nạp CSV và output của ba công cụ vào SQLite, tạo báo cáo

**Ánh xạ output → `scan_finding`:**

| Công cụ | Đường dẫn trong output | `check_id` | `path` | `start_line` | `severity` | CWE |
|---|---|---|---|---|---|---|
| Semgrep | `results[]` | `check_id` | `path` | `start.line` | `extra.severity` | tra từ `semgrep_rule_cwe` (+ override) |
| ZAP | `site[].alerts[].instances[]` | `pluginid` | `uri` | 0 | `riskcode` → HIGH/MEDIUM/LOW/INFO | `cweid` |
| Trivy `Vulnerabilities` | `Results[].Vulnerabilities[]` | `VulnerabilityID` | `Target :: PkgName@InstalledVersion` | 0 | `Severity` | `CweIDs` |
| Trivy `Misconfigurations` | `Results[].Misconfigurations[]` | `ID` | `Target` | `CauseMetadata.StartLine` | `Severity` | (không có) |
| Trivy `Secrets` | `Results[].Secrets[]` | `RuleID` | `Target` | `StartLine` | `Severity` | (không có) |

<details>
<summary><code>load_and_map.py</code> — chạy: <code>python load_and_map.py templates,tool_side mapping.sql approve semgrep=scan.json trivy=trivy.json zap=zap.json</code></summary>

```python
"""Nạp CSV + kết quả scan của Semgrep / Trivy / ZAP vào SQLite rồi chạy mapping.sql.

python load_and_map.py templates,tool_side mapping.sql [approve] semgrep=scan.json trivy=trivy.json zap=zap.json
(các thư mục CSV ngăn bằng dấu phẩy; mỗi công cụ có thể truyền nhiều file, lặp lại tool=đường_dẫn)
"""
import csv, json, pathlib, sqlite3, sys

csv_dirs, sql_file = [pathlib.Path(p) for p in sys.argv[1].split(",")], pathlib.Path(sys.argv[2])
approve = "approve" in sys.argv[3:]                 # chỉ để demo: coi override đề xuất là đã duyệt
inputs = [a.split("=", 1) for a in sys.argv[3:] if "=" in a]

db = sqlite3.connect(":memory:")
for f in sorted(p for d in csv_dirs for p in d.glob("*.csv")):   # mỗi CSV -> một bảng cùng tên, mọi cột TEXT
    with open(f, newline="", encoding="utf-8-sig") as fh:
        rd = csv.reader(fh)
        cols = next(rd)
        db.execute(f"CREATE TABLE {f.stem} ({', '.join(c + ' TEXT' for c in cols)})")
        db.executemany(f"INSERT INTO {f.stem} VALUES ({','.join('?' * len(cols))})", rd)
db.execute("CREATE TABLE scan_finding (finding_id INTEGER PRIMARY KEY, tool TEXT, check_id TEXT, path TEXT,"
           " start_line INTEGER, severity TEXT)")
db.execute("CREATE TABLE scan_finding_cwe (finding_id INTEGER, cwe_id TEXT)")

def cwe_number(v):
    """'CWE-79' / '79' / 79 -> '79'; '-1', '0', '', 'NVD-CWE-Other' -> None."""
    s = str(v).strip().lower().removeprefix("cwe-")
    return s if s.isdigit() and int(s) > 0 else None

def add(tool, check_id, path, line, severity, cwes=()):
    cur = db.execute("INSERT INTO scan_finding (tool, check_id, path, start_line, severity) VALUES (?,?,?,?,?)",
                     (tool, check_id, path, line, severity))
    for c in {cwe_number(c) for c in cwes} - {None}:
        db.execute("INSERT INTO scan_finding_cwe VALUES (?,?)", (cur.lastrowid, c))

ZAP_RISK = {"3": "HIGH", "2": "MEDIUM", "1": "LOW", "0": "INFO"}
for tool, path in inputs:
    d = json.load(open(path, encoding="utf-8"))
    if tool == "semgrep":                           # CWE tra từ catalog rule, không lấy từ finding
        for r in d["results"]:
            add(tool, r["check_id"], r["path"], r["start"]["line"], r["extra"]["severity"])
    elif tool == "trivy":                           # Results[] -> Vulnerabilities / Misconfigurations / Secrets
        for res in d.get("Results", []):
            for v in res.get("Vulnerabilities") or []:
                add(tool, v["VulnerabilityID"], f'{res["Target"]} :: {v["PkgName"]}@{v.get("InstalledVersion", "")}',
                    0, v.get("Severity"), v.get("CweIDs") or [])
            for m in res.get("Misconfigurations") or []:      # Trivy không gắn CWE cho misconfig
                add(tool, m["ID"], res["Target"], (m.get("CauseMetadata") or {}).get("StartLine", 0), m.get("Severity"))
            for s in res.get("Secrets") or []:                # ... và cũng không gắn cho secret
                add(tool, s["RuleID"], res["Target"], s.get("StartLine", 0), s.get("Severity"))
    elif tool == "zap":                             # site[].alerts[].instances[]; cweid là chuỗi, "-1"/"0" = không có
        for site in d.get("site", []):
            for a in site.get("alerts", []):
                for inst in a.get("instances") or [{}]:
                    add(tool, a["pluginid"], inst.get("uri", site.get("@name", "")), 0,
                        ZAP_RISK.get(str(a.get("riskcode")), "INFO"), [a.get("cweid")])
    else:
        sys.exit(f"công cụ không hỗ trợ: {tool}")

if approve:
    db.execute("UPDATE semgrep_cwe_override SET verification_status = 'approved'")
db.executescript(sql_file.read_text(encoding="utf-8"))
for view in ("report_ipa", "report_unmapped"):
    cur = db.execute(f"SELECT * FROM {view} ORDER BY tool, path, start_line")
    print(f"== {view}")
    print(" | ".join(d[0] for d in cur.description))
    for row in cur:
        print(" | ".join(str(x) for x in row))
print("findings:", db.execute("select count(*) from scan_finding").fetchone()[0],
      "| có CWE:", db.execute("select count(distinct finding_id) from finding_cwe").fetchone()[0],
      "| vào IPA:", db.execute("select count(distinct finding_id) from finding_ipa").fetchone()[0],
      "| dòng báo cáo IPA:", db.execute("select count(*) from report_ipa").fetchone()[0])
```
</details>

<details>
<summary><code>mapping.sql</code> — sáu view: rule_cwe_effective, finding_cwe, cwe_ancestor, finding_ipa, report_ipa, report_unmapped</summary>

```sql
-- 1) CWE hiệu lực của rule Semgrep sau khi áp override đã duyệt
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

-- 2) finding -> CWE
--    Semgrep: tra từ catalog rule (check_id = <tiền tố đường dẫn config>.<check_id_suffix>), có áp override.
--    ZAP / Trivy: CWE đi kèm chính finding (bảng scan_finding_cwe do bộ chuyển đổi điền).
CREATE VIEW finding_cwe AS
SELECT f.finding_id, f.tool, f.check_id, f.path, f.start_line, f.severity, e.cwe_id, e.cwe_source
FROM scan_finding f
JOIN rule_cwe_effective e
  ON f.tool = 'semgrep'
 AND (f.check_id = e.check_id_suffix
      OR substr(f.check_id, -length(e.check_id_suffix) - 1) = '.' || e.check_id_suffix)
UNION ALL
SELECT f.finding_id, f.tool, f.check_id, f.path, f.start_line, f.severity, c.cwe_id, 'finding'
FROM scan_finding f JOIN scan_finding_cwe c ON c.finding_id = f.finding_id;

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

-- 5) báo cáo: gộp theo (công cụ, vị trí, mục IPA); best_match = kiểu khớp mạnh nhất
CREATE VIEW report_ipa AS
SELECT fi.tool, fi.path, fi.start_line, fi.ipa_id, i.name_en AS ipa_name,
       COUNT(DISTINCT fi.check_id) AS n_checks,
       GROUP_CONCAT(DISTINCT fi.cwe_id) AS cwe_ids,
       CASE MAX(CASE fi.match_kind WHEN 'exact' THEN 5 WHEN 'narrower' THEN 4 WHEN 'broader' THEN 3
                                   WHEN 'ancestor' THEN 2 ELSE 1 END)
            WHEN 5 THEN 'exact' WHEN 4 THEN 'narrower' WHEN 3 THEN 'broader'
            WHEN 2 THEN 'ancestor' ELSE 'related' END AS best_match
FROM finding_ipa fi JOIN ipa_item i ON i.ipa_id = fi.ipa_id
GROUP BY fi.tool, fi.path, fi.start_line, fi.ipa_id;

-- 6) phần IPA không phủ: có CWE nhưng không có mục IPA / không có CWE
CREATE VIEW report_unmapped AS
SELECT fc.tool, fc.path, fc.start_line, fc.check_id, GROUP_CONCAT(fc.cwe_id) AS cwe_ids, 'OUT_OF_IPA_SCOPE' AS status
FROM finding_cwe fc
WHERE NOT EXISTS (SELECT 1 FROM finding_ipa x WHERE x.finding_id = fc.finding_id)
GROUP BY fc.finding_id
UNION ALL
SELECT f.tool, f.path, f.start_line, f.check_id, '', 'NO_CWE'
FROM scan_finding f
WHERE NOT EXISTS (SELECT 1 FROM finding_cwe c WHERE c.finding_id = f.finding_id);
```
</details>

**Khi chuyển sang PostgreSQL:** đổi cột số sang `INTEGER` (`cwe_id`, `related_cwe_id`, `start_line`), thêm khóa chính/ngoại như bảng ở mục 8, thay `substr(..., -n)` bằng `right(f.check_id, length(...) + 1)`, đổi `GROUP_CONCAT` thành `string_agg`. Vì dữ liệu nhỏ (khoảng 1.400 dòng CWE, 1.800 dòng rule), cách đơn giản nhất là **nạp lại toàn bộ trong một transaction** mỗi lần cập nhật, không cần UPSERT từng dòng; git giữ lịch sử.

---

## 10 · Cập nhật liên tục khi IPA (và các nguồn khác) thay đổi

### 10.1 Từng nguồn: phát hiện thay đổi thế nào

| Nguồn | Phát hiện thay đổi | Tần suất đề xuất | Khi có thay đổi |
|---|---|---|---|
| IPA "安全なウェブサイトの作り方" (HTML/PDF) | Băm (SHA-256) phần nội dung chính đã chuẩn hóa (bỏ menu, chân trang, script); phụ trợ `ETag`/`Last-Modified`; tìm chuỗi "改訂第N版" so với cột `edition` | Hằng tuần | Mở PR kèm diff văn bản; **người** cập nhật `ipa_item`/`ipa_countermeasure`/`ipa_cwe_map` |
| IPA trang CWE (JA, EN) | Như trên | Hằng tuần | Cảnh báo, người xem có đổi cách IPA dùng CWE không |
| MITRE CWE | So `version` từ REST API (hoặc `ETag` của `cwec_latest.xml.zip`) với `source_version.current_version` **[chưa xác minh endpoint]** | Hằng tuần | Tải XML → `cwe_xml_to_csv.py` → diff → chạy Q4 (CWE trong `ipa_cwe_map` còn tồn tại và không Deprecated) → PR |
| `semgrep-rules` | `git ls-remote <repo> HEAD` so với `ruleset_commit` | Hằng ngày/tuần | `git pull` → `extract_semgrep_rules.py` → diff: rule mới chưa được map, rule đổi CWE, override không còn khớp → PR |
| `zap-extensions` (scan rule) | `git ls-remote` so với commit đã lưu | Hằng tuần | `extract_zap_rules.py` → diff: rule mới, rule đổi/bỏ CWE → PR. Thêm bước kiểm tra số file `*ScanRule.java` có khai báo CWE không tụt (phát hiện rule đổi cách khai báo làm script bỏ sót) |
| Trivy: `trivy-db` (nguồn của `CweIDs`) | Digest/phiên bản của artifact `ghcr.io/aquasecurity/trivy-db` (cập nhật thường xuyên) | Mỗi lần quét | **Ghi phiên bản DB vào báo cáo** để tái hiện; không cần commit dữ liệu DB |
| Trivy: schema output và `trivy-checks` | `git ls-remote`; chạy `grep -ril cwe` trên `trivy-checks` và kiểm tra `CweIDs` còn trong struct output | Hằng tháng | Nếu Trivy bắt đầu gắn CWE cho misconfig, cập nhật bộ chuyển đổi (mục 9.4) và bỏ bảng tra tự biên soạn |
| JVN iPedia (tùy chọn) | Feed/API **[chưa xác minh]** | Hằng quý | Cập nhật thống kê CWE phổ biến |

### 10.2 Luồng

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

- **Không tự merge** thay đổi từ IPA: đổi bản, đổi số mục, đổi câu chữ cần người đọc tiếng Nhật duyệt. Với bảng thuần trích xuất (`semgrep_rule_cwe`, `zap_rule_cwe`, `cwe_catalog`, `cwe_relation`) có thể cân nhắc tự merge khi mọi cổng chất lượng đạt.
- **Hash đổi chưa chắc nội dung đổi**: trang web hay đổi menu/chân trang. Hash chỉ phần nội dung chính, và vẫn để người xem diff.
- **Mapping sai âm thầm là rủi ro lớn nhất.** Mỗi lần CWE đổi (deprecate, đổi tên, đổi cha), cổng Q4 phải chặn PR nếu `ipa_cwe_map` còn trỏ vào CWE không hợp lệ.
- **Phiên bản dữ liệu:** commit `source_version.csv` cùng dữ liệu; gắn tag dạng `kb-YYYY.MM.DD`. Báo cáo scan ghi tag này (cùng commit rule Semgrep, commit rule ZAP, phiên bản DB Trivy) để tái hiện kết quả sau này.
- **KB IPA + NVD là đầu ra chính của pipeline** (thư mục `kb/`, [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md) mục 7). Phần phía công cụ ở đây (catalog rule, override) chỉ cần cập nhật khi rule của công cụ đổi.
- **Giữ nguồn ngoài đường găng:** nếu IPA/MITRE tạm không truy cập được, job báo `error` cho nguồn đó và dùng bản dữ liệu đã commit, không làm hỏng pipeline scan.

### 10.3 Bản phác thảo GitHub Actions (**chưa chạy thử**)

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
          title: "security_scan: cập nhật nguồn IPA / CWE / Semgrep / ZAP / Trivy"
          body-path: projects/security_scan/reports/kb_diff.md
          labels: needs-human-review
```

Runner GitHub có Internet mở; môi trường chạy trong sandbox/cloud nội bộ thì phải mở các host: `www.ipa.go.jp`, `cwe.mitre.org`, `cwe-api.mitre.org`, `jvndb.jvn.jp`, `github.com`, `raw.githubusercontent.com`, `pypi.org`, và cho Trivy `ghcr.io` (DB lỗ hổng). IPA có thể giới hạn truy cập từ một số vùng/bot; thử sớm.

---

## 11 · Rủi ro, việc cần người, bước tiếp theo

**Rủi ro**

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Bản seed IPA↔CWE sai/lệch so với IPA | Cao | Không dùng chính thức trước khi đối chiếu PDF; mọi dòng `seed_unverified`; cổng Q2/Q5 |
| 11 mục IPA chỉ phủ ~1/4 rule | Cao với mục tiêu "tuân thủ IPA" | Giữ `OUT_OF_IPA_SCOPE`; mở rộng nguồn IPA; dùng JVN iPedia xếp hạng ưu tiên |
| **Trivy và ZAP chưa được chạy thật trong phiên này** | Trung bình | Các kết luận về schema đọc từ mã nguồn và dữ liệu mẫu của dự án; cần chạy thử trên mục tiêu hợp lệ để xác nhận (đặc biệt giá trị `cweid` khi không có CWE, và tỉ lệ `CweIDs` rỗng trên DB thật) |
| Trivy: phần lớn finding ngoài tầm IPA (misconfig, secret, CVE thư viện) | Trung bình | Báo cáo tách nhóm; chỉ dùng IPA để *phân loại* CVE, không dùng đối sách IPA để vá thư viện |
| ZAP active scan gây hại cho mục tiêu | Cao nếu dùng sai | Chỉ quét hệ thống được cấp phép; dùng môi trường staging; bắt đầu bằng baseline (passive) |
| Tag CWE của Semgrep (và có thể của ZAP/Trivy) sai | Trung bình | Bảng override có duyệt (hiện mới cho Semgrep, xem mục 4.4); so sánh với biến thể cùng tên |
| Rule/DB thay đổi theo thời gian khiến kết quả không tái hiện | Trung bình | Ghi `ruleset_commit`, commit rule ZAP, phiên bản DB Trivy; ghim khi chạy báo cáo chính thức |
| Giấy phép/điều khoản | Cần kiểm tra | **Semgrep Rules License v1.0** (đọc trước khi nhúng/phân phối lại rule); điều khoản sử dụng của **CWE** (file `cwe-tou` trong gói); điều khoản của **IPA** khi sao chép nguyên văn (**[chưa xác minh]**); điều khoản của các nguồn dữ liệu lỗ hổng mà Trivy tải về. Nếu chưa rõ, `text_ja` để trống, chỉ lưu số mục + URL + diễn giải tiếng Việt |
| KB (`kb/`) bị coi là chân lý dù mapping IPA dựa trên seed chưa xác minh | Trung bình | Mọi dòng mang `mapping_status`; tài liệu 03 và README ghi rõ |
| Bản CWE dùng thử (4.14) cũ | Thấp–trung bình | Chỉ dùng cho dựng pipeline; tải bản mới nhất trước khi dùng thật |

**Việc cần người**

1. Cho phép host `www.ipa.go.jp`, `cwe.mitre.org`, `cwe-api.mitre.org`, `semgrep.dev`, `jvndb.jvn.jp` (hoặc gửi PDF/HTML đã tải) để đối chiếu 4 URL ban đầu; thêm `ghcr.io` nếu muốn tải DB của Trivy trong môi trường này.
2. Người đọc được tiếng Nhật đối chiếu: tên 11 mục, số bản (đang giả định "改訂第7版"), mã CWE IPA thật sự dùng, nguyên văn đối sách.
3. Quyết định phạm vi: chỉ 11 mục web, hay mở rộng sang tài liệu IPA khác cho phần `OUT_OF_IPA_SCOPE`.
4. Duyệt bốn override đề xuất: OV-0001/0002 (bằng chứng mạnh), OV-0004 (dựa trên đọc nội dung rule), OV-0003 (chỉ là nhận định, chưa phải bằng chứng).
5. Chạy thử Trivy và ZAP thật trên ứng dụng/ảnh container của bạn (hoặc ứng dụng thử nghiệm có lỗi cố ý), rồi đưa file JSON vào loader để xác nhận số liệu. Trong phiên này, việc build Trivy từ mã nguồn bên ngoài để chạy bị hệ thống phân quyền chặn nên mình không làm; muốn mình chạy lại thì cần bạn cấp quyền rõ ràng, hoặc chạy ở máy của bạn.

**Bước tiếp theo đề xuất**

1. `ipa_item` và đối sách đã xong nhờ checklist bản 7 (2026-10-28). Còn lại: đối chiếu và nâng `ipa_cwe_map` lên `verified`; điền `source_version.csv` cho các nguồn còn `not_fetched`.
2. Tải CWE mới nhất, chạy `cwe_xml_to_csv.py`, chạy cổng Q4.
3. Chạy `extract_semgrep_rules.py` và `extract_zap_rules.py` để có bản đầy đủ; quét một ứng dụng thật có lỗi cố ý bằng cả ba công cụ để đo độ phủ trên finding (không chỉ trên rule).
4. Nếu thấy CWE sai ở ZAP/Trivy: mở rộng bảng override thêm cột `tool`.
5. Viết `scripts/security_kb/refresh.py` và workflow; chạy thử không `--merge` trong 2–3 tuần để xem tần suất thay đổi thực tế.

---

## 12 · Nguồn

Đã đọc trực tiếp / chạy thật trong phiên:
- Semgrep 1.182.1 (PyPI) và repo [`semgrep/semgrep-rules`](https://github.com/semgrep/semgrep-rules) commit `16b9e6d` (file `metadata-schema.yaml.schm`, `LICENSE`, các rule YAML).
- Gói PyPI `cwe2` 3.0.0: dữ liệu CWE 4.14 (`cwec_v4.14.xml`, CSV mapping, `cwe.ABOUT`, giấy phép `cwe-tou`).
- [`aquasecurity/trivy`](https://github.com/aquasecurity/trivy) commit `201dda0` (2026-10-27): `LICENSE`, `pkg/types`, `pkg/sbom/cyclonedx/marshal.go`, `pkg/db/db.go`, `integration/testdata/*.json.golden`.
- [`aquasecurity/trivy-checks`](https://github.com/aquasecurity/trivy-checks) commit `f9099b7` (2026-10-26): `LICENSE` (MIT), metadata rego.
- Module Go `github.com/aquasecurity/trivy-db` (qua proxy.golang.org, phiên bản ghim trong `go.mod` của Trivy): `pkg/types/types.go`, `pkg/vulnsrc/nvd/nvd.go`, `pkg/vulnsrc/vulnerability/vulnerability.go`.
- [`zaproxy/zaproxy`](https://github.com/zaproxy/zaproxy) commit `d5da218` (2026-10-27): `LICENSE`, `README.md`, `Alert.java`, `docker/zap-*.py`.
- [`zaproxy/zap-extensions`](https://github.com/zaproxy/zap-extensions) commit `51e4155` (2026-10-26): `LICENSE`, scan rule Java, template và fixture của add-on *reports*.

Chỉ qua kết quả WebSearch (chưa đọc trang gốc):
- IPA, trang CWE tiếng Nhật: <https://www.ipa.go.jp/security/vuln/CWE.html>
- IPA, trang CWE tiếng Anh: <https://www.ipa.go.jp/en/security/vulnerabilities/cwe.html>
- IPA, mục SCAP/CWE: <https://www.ipa.go.jp/security/vuln/scap/cwe.html>
- Báo cáo JVN iPedia theo quý của IPA, ví dụ: <https://www.ipa.go.jp/en/security/vulnerabilities/jvn/ipedia2023q2_en.html>
- Tài liệu Semgrep về trường JSON/SARIF: <https://semgrep.dev/docs/semgrep-appsec-platform/json-and-sarif>
- Tài liệu mua sắm thành phố Yokohama (bên thứ ba, có gắn CWE-601, CWE-434): <https://en.city.yokohama.lg.jp/business/nyusatsu/kakukukyoku/2019/itaku/kankyo/enekaru2019.files/0011_20190319.pdf>
- Tài liệu ZAP về báo cáo JSON truyền thống (có `cweid`, `wascid`): <https://www.zaproxy.org/docs/desktop/addons/report-generation/report-traditional-json/>
- Ghi chú phát hành Trivy v0.10.0 (thêm CWE-ID vào JSON): <https://github.com/aquasecurity/trivy/releases/tag/v0.10.0>
- Tài liệu báo cáo của Trivy: <https://trivy.dev/docs/v0.59/guide/configuration/reporting/>

URL bạn cung cấp nhưng chưa đọc được (host bị chặn): <https://www.ipa.go.jp/>, <https://www.ipa.go.jp/security/vuln/websecurity/about.html>, <https://cwe.mitre.org/about/new_to_cwe.html>, <https://semgrep.dev/>.
