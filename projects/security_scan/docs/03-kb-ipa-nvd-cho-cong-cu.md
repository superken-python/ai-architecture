# 03 · Knowledge base IPA + NVD để Semgrep, ZAP, Trivy tra cứu

Ngày: 2026-10-27, cập nhật 2026-10-28 (KB tối giản còn 6 + 3 cột; 11 mục IPA và 47 đối sách đối chiếu với checklist bản 7 của IPA) · Đọc cùng: [01 · Nghiên cứu IPA, CWE, Semgrep](01-nghien-cuu-ipa-cwe-semgrep.md), [02 · Phía công cụ](02-mapping-semgrep-ipa-va-cap-nhat.md), [05 · Runbook dựng KB (tiếng Anh)](05-kb-build-runbook.md), [06 · Ý nghĩa từng cột của KB (tiếng Anh)](06-kb-field-reference.md). Nhãn nguồn dùng như tài liệu 01: **[đã kiểm chứng]** (mình tự chạy/đọc dữ liệu thật), **[tìm kiếm web]** (đoạn trích, chưa đọc trang gốc), **[chưa xác minh]**.

## 0 · Đính chính hướng thiết kế

Lần trước mình làm ngược: lấy rule của Semgrep/ZAP đổ vào template (`exports/ipa_map_all_tools.csv`, đã gỡ). Đúng ra **IPA và NVD là tài liệu tham chiếu**. Cần export dữ liệu tổng hợp của IPA + NVD thành một knowledge base (KB), rồi các công cụ chỉ đưa ra *khóa* (CWE, CVE) để tra vào KB đó.

```
 Semgrep ─┐ CWE                 ┌──────────────── KB IPA + NVD (không phụ thuộc công cụ) ───────────────┐
 ZAP ─────┼────────────────────►│ kb_cwe.csv (6 cột): CWE → tên CWE, mục IPA (mã, tên tiếng Nhật),      │
          │                     │                     kiểu khớp, trạng thái duyệt                       │
 Trivy ───┘ CVE ───────────────►│ kb_cve.csv (3 cột): CVE → CWE được chọn + nguồn (NVD, CNA/ADP, JVN);  │
            (CWE của Trivy chỉ  │                     mục IPA tra tiếp qua kb_cwe.csv                   │
             dùng khi KB thiếu) └─────▲───────────────────────▲─────────────────────────▲───────────────┘
                                      │ MITRE CWE             │ NVD: CVE JSON 2.0       │ IPA: 安全なウェブサイトの作り方
                                      │ (cây view 1000)       │ + JVN iPedia (CWE)      │ checklist bản 7 + bảng IPA↔CWE
```

Dữ liệu rule của công cụ (catalog rule, override CWE sai của rule) chuyển sang thư mục [`tool_side/`](../tool_side/). Đó là việc chuẩn hóa *trước khi* tra KB, không phải nội dung KB ([tài liệu 02](02-mapping-semgrep-ipa-va-cap-nhat.md)).

## 1 · Tóm tắt

1. **KB gồm hai file theo hai khóa, tối giản từ 2026-10-28**: [`kb/kb_cwe.csv`](../kb/kb_cwe.csv) (khóa CWE, 6 cột) nói CWE thuộc mục IPA nào; `kb_cve.csv` (khóa CVE, 3 cột) nói CVE có CWE nào. Semgrep và ZAP tra `kb_cwe`; Trivy tra `kb_cve` lấy CWE rồi tra tiếp `kb_cwe`. Mỗi dữ kiện chỉ lưu một chỗ, nên sửa mapping IPA chỉ đổi `kb_cwe`. Không gộp làm một vì NVD có hơn 415.000 CVE cập nhật mỗi ngày, còn phần CWE + IPA nhỏ và đổi chậm. Ý nghĩa từng cột: [tài liệu 06](06-kb-field-reference.md).
2. **Đã dựng thật**: `kb_cwe.csv` đầy đủ (1.375 khóa: 963 weakness, 409 category, 3 mã giả của NVD/JVN) và [`kb/kb_cve.sample.csv`](../kb/kb_cve.sample.csv) (23 CVE thật, ghép NVD với JVN iPedia). Bản `kb_cve` đầy đủ sinh bằng script ở mục 6: toàn bộ lịch sử NVD (415.469 CVE) ra file 12 MB (bản 35 cột cũ: 271 MB), thời gian và bộ nhớ ở [tài liệu 05](05-kb-build-runbook.md). Bản tối giản cho đúng cùng kết quả với bản rộng cũ trên mọi CVE (tài liệu 06 mục 8).
3. **Một CVE có thể mang CWE khác nhau tùy nguồn và tùy thời điểm**, nên bộ build đọc CWE của **từng nguồn** rồi chọn theo một quy tắc cố định; KB lưu CWE được chọn và nguồn của nó. Ví dụ thật: Log4Shell có JVN = 20, CNA = 20/400/502, NVD = 917. Với jquery `CVE-2019-11358`, NVD hiện ghi CWE-1321, GHSA ghi cả 1321 lẫn 79, còn DB kiểm thử của Trivy (chụp dữ liệu NVD năm 2021) ghi CWE-79: cùng nguồn NVD nhưng khác thời điểm (xem [tài liệu 04](04-thuat-ngu-so-sanh-va-cach-map.md)).
4. **JVN iPedia (của IPA) gắn CWE cho cả bản ghi JVNDB**, có thể chứa nhiều CVE. Lấy CWE của JVN làm mặc định sẽ làm phình mapping, nên mặc định ưu tiên NVD rồi CNA/ADP, và JVN để lấp chỗ trống (`--prefer jvn` để đảo thứ tự).
5. **NVD tự gắn CWE cho rất ít CVE mới**: năm 2025 chỉ 12,5% CWE do chính NVD gắn, 83,6% do CNA/ADP. KB nào chỉ lấy CWE `nvd@nist.gov` sẽ mất phần lớn dữ liệu.
6. **Độ phủ của 11 mục IPA trên CVE thật cao hơn nhiều so với trên rule công cụ**: năm 2025 có **58,8%** CVE (không tính Rejected) rơi vào một mục IPA. Trên rule của Semgrep/ZAP con số này chỉ khoảng 25% (tài liệu 02). Phần ngoài IPA lớn nhất: CWE-284, 476, **434 (upload file)**, **98 (PHP file inclusion)**, 200, 502.
7. **Dữ liệu IPA chính thức**: người dùng cung cấp file checklist Excel của 安全なウェブサイトの作り方 改訂第7版 ([000044403.xlsx](https://www.ipa.go.jp/security/vuln/websecurity/ug65p900000196e2-att/000044403.xlsx)). 11 mục (số thứ tự, tên tiếng Nhật) khớp bản seed và đã chuyển sang `verified`; 47 đối sách (32 根本的解決, 15 保険的対策) đã nhập nguyên văn. File này **không có mã CWE**, nên bảng IPA↔CWE vẫn là seed.
8. **Cập nhật liên tục có sẵn cơ chế kiểm tra**: mirror NVD có file `.meta` chứa sha256 (đã đối chiếu khớp), JVN iPedia có `checksum.txt` liệt kê sha256 của mọi feed.
9. **Giới hạn**: `services.nvd.nist.gov`, `jvndb.jvn.jp`, `www.ipa.go.jp` bị chặn trong môi trường này. Dữ liệu NVD lấy qua mirror `fkie-cad/nvd-json-data-feeds` (snapshot 2026-10-27). Dữ liệu JVN lấy từ fixture thật trong repo `vuls-data-update` (snapshot 2023-11-02). Mapping CWE↔IPA vẫn là bản seed **chưa xác minh** (checklist của IPA không có mã CWE).

---

## 2 · Nguồn dữ liệu (nghiên cứu)

### 2.1 NVD (NIST)

| Nội dung | Chi tiết | Nhãn |
|---|---|---|
| API chính thức | `https://services.nvd.nist.gov/rest/json/cves/2.0`; khóa API gửi trong header `apiKey`; giới hạn khoảng 5 request/30 giây không có khóa, 50 có khóa; lọc khoảng thời gian tối đa 120 ngày; đồng bộ tăng dần bằng `lastModStartDate`/`lastModEndDate`; có tham số `cweId` | [tìm kiếm web] |
| Feed JSON cũ | NIST ngừng các feed JSON của NVD từ 2023-12-15 | theo README của mirror |
| Mirror dùng trong phiên này | [`fkie-cad/nvd-json-data-feeds`](https://github.com/fkie-cad/nvd-json-data-feeds) (Fraunhofer FKIE): đồng bộ NVD mỗi 2 giờ, release mỗi ngày 00:00 UTC, 415.377 CVE (2026-10-27); feed theo năm `CVE-<YEAR>.json.xz`, `CVE-Recent` (CVE mới 8 ngày), `CVE-Modified` (sửa/mới 8 ngày); mỗi feed có `.meta` (`lastModifiedDate`, `size`, `sha256`); repo lưu mỗi CVE một file JSON | [đã kiểm chứng] |
| Định dạng feed release | `{"timestamp", "cve_count", "feed_name", "source", "cve_items": [...]}`; mỗi phần tử là một bản ghi CVE như API 2.0 | [đã kiểm chứng] |
| Điều khoản mirror | README có "Non-Endorsement Clause" (dùng dữ liệu NVD nhưng không được NVD bảo chứng); không tìm thấy file LICENSE | [đã kiểm chứng] / giấy phép [chưa xác minh] |

**Cấu trúc một bản ghi CVE** (đọc từ bản ghi thật, ví dụ `CVE-2014-0160`, `CVE-2021-44228`) **[đã kiểm chứng]**:

| Trường | Ý nghĩa cho KB |
|---|---|
| `id`, `sourceIdentifier` | Mã CVE; CNA đã cấp (ví dụ `security@apache.org`) |
| `published`, `lastModified`, `vulnStatus` | Ngày; trạng thái xử lý của NVD. Giá trị gặp trong feed 2025: `Analyzed`, `Deferred`, `Modified`, `Rejected`, `Awaiting Analysis`, `Undergoing Analysis`, `Received` |
| `weaknesses[]` | Mỗi phần tử có `source` (`nvd@nist.gov`, email CNA hoặc UUID của ADP), `type` (`Primary`/`Secondary`), `description[].value` = `CWE-79` hoặc mã giả `NVD-CWE-Other`, `NVD-CWE-noinfo`. Có CVE không có phần tử nào |
| `metrics` | `cvssMetricV40`, `cvssMetricV31`, `cvssMetricV30`, `cvssMetricV2` (mỗi mục có `source`, `type`, `cvssData.baseScore/baseSeverity/vectorString`); `ssvcV203` từ nguồn có UUID `134c704f-9b21-4f2e-91b3-4a467353bcc0` (theo hiểu biết của mình là CISA ADP, **[chưa xác minh]**) |
| `cisaExploitAdd`, `cisaActionDue`, `cisaRequiredAction`, `cisaVulnerabilityName` | CVE nằm trong danh mục KEV của CISA (ví dụ Heartbleed, Log4Shell) |
| `configurations[].nodes[].cpeMatch[]` | CPE 2.3 + khoảng phiên bản; KB không cần vì Trivy tự so gói |
| `descriptions[]` | Mô tả `en` (và `es`) |

**CWE mà NVD dùng = view 1003 của MITRE** ("Weaknesses for Simplified Mapping of Published Vulnerabilities"). Trong CWE 4.14, view này có **130 CWE** (37 nút gốc + 93 nút con) **[đã kiểm chứng]**. Chỉ 24 trong số đó khớp 11 mục IPA theo bản seed. Đáng chú ý: **CWE-113 (HTTP header injection), CWE-93 (CRLF) và CWE-285 không thuộc view 1003**. Vì vậy CVE trên NVD hầu như không mang các mã này, và mục 1.7/1.8 của IPA hiếm khi khớp qua dữ liệu NVD.

### 2.2 IPA: JVN iPedia

JVN iPedia là cơ sở dữ liệu lỗ hổng của IPA, mã dạng `JVNDB-YYYY-NNNNNN`. Mình không truy cập được `jvndb.jvn.jp`. Thay vào đó mình đọc **fixture thật** (bản sao feed của JVN, snapshot 2023-11-02) và mã nguồn của hai công cụ Apache-2.0 vẫn tải JVN hằng ngày: [`vulsio/go-cve-dictionary`](https://github.com/vulsio/go-cve-dictionary) và [`MaineK00n/vuls-data-update`](https://github.com/MaineK00n/vuls-data-update).

| Feed | URL | Nhãn |
|---|---|---|
| Danh sách feed + sha256 | `https://jvndb.jvn.jp/ja/feed/checksum.txt` (JSON: `url`, `filename`, `sha256`, `size`, `lastModified`) | [đã kiểm chứng: định dạng trong fixture, URL trong mã nguồn] |
| RSS mới / mới cập nhật | `https://jvndb.jvn.jp/ja/rss/jvndb_new.rdf`, `https://jvndb.jvn.jp/ja/rss/jvndb.rdf` | [đã kiểm chứng] |
| RSS theo năm | `https://jvndb.jvn.jp/ja/rss/years/jvndb_YYYY.rdf` (năm 2022: 35 MB) | [đã kiểm chứng] |
| Chi tiết theo năm (VULDEF 3.2) | `https://jvndb.jvn.jp/ja/feed/detail/jvndb_detail_YYYY.rdf` (năm 2022: 72 MB) | [đã kiểm chứng] |
| MyJVN API | `getVulnOverviewList` (JVNRSS, lọc theo CPE hoặc từ khóa như số CVE), `getVulnDetailInfo` (VULDEF 3.2), `getStatistics` (lọc theo CWE/CVSS) | [tìm kiếm web] |

**Feed RSS** (jvnrss 2.0): mỗi `<item>` có `sec:identifier` (mã JVNDB) và `sec:references source="CVE"|"NVD" id="CVE-…"`. **CWE** nằm ở `sec:references` **không có `source`**, với `id="CWE-79"` và `title="クロスサイトスクリプティング(CWE-79)"`. Ngoài ra có `sec:cpe` (CPE 2.2), `sec:cvss` (CVSS v2/v3 do **IPA tự chấm**) và các ngày. **[đã kiểm chứng]**

**Feed chi tiết** (VULDEF 3.2): `Title`, `Overview`, `Impact/Cvss`, **`Solution` (đối sách bằng tiếng Nhật cho từng lỗ hổng)**, `Related/RelatedItem type="advisory"` (CVE, JVN#), `RelatedItem type="cwe"` (`VulinfoID` = CWE-79, `Title` tiếng Nhật, URL `https://jvndb.jvn.jp/ja/cwe/CWE-79.html`), `DateLastUpdated`. **[đã kiểm chứng]**

**Tên CWE tiếng Nhật thu được từ dữ liệu thật** (trước 2026-10-28 nằm trong cột `cwe_name_ja` của `kb_cwe.csv`; bản tối giản đã bỏ cột này; template `cwe_catalog.csv` có 5 tên trong số này): CWE-20 不適切な入力確認, CWE-79 クロスサイトスクリプティング, CWE-89 SQLインジェクション, CWE-94 コード・インジェクション, CWE-352 クロスサイトリクエストフォージェリ, CWE-399 リソース管理の問題, CWE-476 NULL ポインタデリファレンス, CWE-640 パスワードを忘れた場合の脆弱なパスワードリカバリの仕組み, mã giả `CWE-noinfo` 情報不足. Tên đầy đủ cho mọi CWE cần đọc toàn bộ feed theo năm. Lưu ý tên của JVN có thể khác cách viết trong tài liệu hướng dẫn của IPA (ví dụ `クロスサイト・スクリプティング` có dấu `・`).

Ghi chú khi dùng: `go-cve-dictionary` bỏ các mục mà phần mô tả chứa `** 未確定 **`, `** サポート外 **` hoặc `** 削除 **`. Bộ build ở mục 6 chưa lọc các mục này (fixture không có mục nào như vậy để thử).

### 2.3 IPA: 安全なウェブサイトの作り方

Như tài liệu [01](01-nghien-cuu-ipa-cwe-semgrep.md) và [02](02-mapping-semgrep-ipa-va-cap-nhat.md): 11 mục, đối sách gốc rễ/bảo hiểm, bảng IPA↔CWE. Từ 2026-10-28, `templates/ipa_item.csv` (11 mục) và `ipa_countermeasure.csv` (47 đối sách, mã như `1-(i)-a`, `text_ja` nguyên văn, bản dịch EN/VI của mình) **đã đối chiếu với checklist Excel bản 7 của IPA** (sha256 `07df4d1718514d6b66cb96e7c3e7ce6270497516363278ecfd0868e8f3cb7a75`, ghi trong `source_version.csv`). Checklist không có mã CWE, nên `ipa_cwe_map.csv` vẫn là **seed chưa xác minh**.

### 2.4 So sánh CWE của NVD và JVN trên 16 CVE thật

| JVNDB | CVE | JVN (IPA) | NVD (`nvd@nist.gov`) | CNA / ADP | Nhận xét |
|---|---|---|---|---|---|
| JVNDB-2022-000001 | CVE-2021-20877 | 79 | 79 | | Trùng |
| JVNDB-2022-000002 | CVE-2022-0180 / 0181 / 0182 | 79 + 352 (cả bản ghi) | 352 / 79 / 79 | | **JVN gắn theo bản ghi, NVD gắn theo từng CVE** |
| JVNDB-2021-005429 | CVE-2021-44228 | 20 | 917 (Secondary) | 20, 400, 502 | Mỗi nguồn một kiểu |
| JVNDB-2023-000001 | CVE-2022-47318 | 94 | NVD-CWE-noinfo | 94 | JVN và ADP cụ thể hơn NVD |
| JVNDB-2022-020469 | CVE-2022-46723 | CWE-noinfo | NVD-CWE-noinfo | 787 | Chỉ ADP có CWE |
| JVNDB-2023-004814 | CVE-2023-0078 | 79 | (không có) | | Chỉ JVN có CWE |
| JVNDB-2011-001013 | CVE-2011-0346 | 399 (category) | 399 | 416 | NVD/JVN dùng category cũ |
| JVNDB-2023-002068 | CVE-2022-25027 | 640 | 640 | 287 | ADP khác |

Sáu CVE còn lại: `CVE-2022-46648`, `CVE-2023-23001`, `CVE-2023-23006` trùng ở cả ba nguồn (94, 476, 476); `CVE-2013-10019` có JVN và CNA cùng ghi 89 nhưng NVD không gắn; `CVE-2022-22292` có JVN và NVD đều ghi "không đủ thông tin" trong khi CNA ghi CWE-280; `CVE-2007-0851` chỉ có `NVD-CWE-Other`.

---

## 3 · Template CSV của KB

Từ 2026-10-28 hai file chỉ giữ những cột cần cho việc tra cứu: `kb_cwe.csv` còn **6 cột** (trước là 23), `kb_cve.csv` còn **3 cột** (trước là 35). Hai nguyên tắc: (1) một cột chỉ ở lại nếu việc tra cứu hoặc báo cáo IPA cần nó và không cột nào khác cho được thông tin đó; (2) mỗi dữ kiện lưu một chỗ: `kb_cve` nói CVE có CWE nào, `kb_cwe` nói CWE thuộc mục IPA nào. Ý nghĩa chi tiết từng cột, các trạng thái tính lúc tra, và chỗ lấy lại các cột đã bỏ: [tài liệu 06 (tiếng Anh)](06-kb-field-reference.md).

### 3.1 Hai file, hai khóa

| File | Khóa | Công cụ dùng | Cỡ | Đổi khi nào |
|---|---|---|---|---|
| [`kb/kb_cwe.csv`](../kb/kb_cwe.csv) | `cwe_id` dạng `CWE-79` (cả mã giả `NVD-CWE-noinfo`, `NVD-CWE-Other`, `CWE-noinfo`) | Semgrep, ZAP; Trivy (sau khi lấy CWE từ `kb_cve`, hoặc dùng CWE của chính Trivy) | 6 cột, 1.376 dòng, 91 KB; **đầy đủ** | Khi CWE hoặc mapping IPA đổi: vài lần mỗi năm, duyệt qua PR |
| `kb_cve.csv` | `cve_id` | Trivy (và mọi công cụ báo CVE) | 3 cột; 415.469 dòng, 12 MB cho toàn bộ lịch sử NVD (bản 35 cột cũ: 271 MB) | Mỗi ngày; sinh lại bằng script, không commit |
| [`kb/kb_cve.sample.csv`](../kb/kb_cve.sample.csv) | `cve_id` | Mẫu | 23 CVE thật | Mẫu cột và dữ liệu, không phải bản đầy đủ |

UTF-8, dấu phẩy, danh sách trong ô ngăn bằng `|`, không có ngày giờ sinh file. Nhờ vậy sinh lại cho cùng dữ liệu thì ra đúng từng byte.

### 3.2 `kb_cwe.csv`: một dòng cho mỗi (CWE, mục IPA)

CWE không thuộc mục IPA nào vẫn có một dòng (bốn cột cuối để trống), để công cụ tra mã nào cũng thấy.

| Cột | Ý nghĩa | Nguồn |
|---|---|---|
| `cwe_id` | `CWE-79`, hoặc mã giả `NVD-CWE-Other`, `NVD-CWE-noinfo`, `CWE-noinfo` | MITRE (mã giả do bộ build thêm) |
| `cwe_name_en` | Tên CWE của MITRE; với mã giả là mô tả ý nghĩa | MITRE |
| `ipa_id` | Mục IPA `IPA-WEB-01` … `IPA-WEB-11`; trống nếu CWE không thuộc mục nào | `templates/ipa_cwe_map.csv`, hoặc thừa hưởng từ tổ tiên |
| `ipa_name_ja` | Tên mục IPA tiếng Nhật, đúng như checklist bản 7 | `templates/ipa_item.csv` |
| `match_kind` | `exact`/`narrower`/`broader`/`related` (trực tiếp từ `ipa_cwe_map`) hoặc `ancestor` (CWE chưa có dòng riêng, thừa hưởng mục IPA từ tổ tiên ≤ 4 cấp theo view 1000 mà dòng mapping là `exact`) | IPA + MITRE |
| `mapping_status` | Trạng thái duyệt của dòng mapping (hiện mọi dòng `seed_unverified`) | `ipa_cwe_map.verification_status` |

Bản hiện tại: 1.375 khóa CWE, 102 CWE map được vào mục IPA (103 dòng vì CWE-93 thuộc cả 1.7 và 1.8), 1.270 CWE ngoài IPA, 3 mã giả. Phiên bản CWE (4.14) không còn là một cột: `build_kb_cwe.py` in ra khi chạy, ghi vào `source_version.csv` (dòng `mitre_cwe_catalog`).

### 3.3 `kb_cve.csv`: một dòng cho mỗi CVE

| Cột | Ý nghĩa |
|---|---|
| `cve_id` | Mã CVE |
| `cwe_selected` | CWE dùng cho CVE này (nhiều mã ngăn bằng `\|`), hoặc một mã giả; trống khi không có |
| `cwe_selected_from` | `nvd`, `cna_adp`, `jvn`, `pseudo` (các nguồn chỉ có mã giả), `none` (không nguồn nào có CWE), `rejected` (NVD đã đánh dấu Rejected: bỏ finding của CVE này) |

Mục IPA của một CVE không lưu ở đây mà tra qua `kb_cwe` theo từng mã trong `cwe_selected` (SQL mẫu ở tài liệu 06 mục 4). CWE riêng của từng nguồn, CVSS, KEV và thông tin JVN đã bỏ khỏi file. `build_kb_cve.py` vẫn đọc mọi nguồn để chọn, và in ra số CVE mà các nguồn lệch nhau (17.897 trên toàn bộ lịch sử ngày 2026-10-28).

### 3.4 Chọn CWE cho một CVE

Mặc định (`--prefer nvd`): lấy **nguồn đầu tiên có CWE thật** theo thứ tự NVD → CNA/ADP → JVN. Nếu không nguồn nào có CWE thật thì giữ mã giả (`NVD-CWE-noinfo`, `CWE-noinfo`…). `--prefer jvn` đặt JVN lên đầu.

Vì sao mặc định không ưu tiên JVN, trên dữ liệu thật:

| CVE | `--prefer nvd` | `--prefer jvn` |
|---|---|---|
| CVE-2022-0181 | CWE-79 → IPA-WEB-05 | CWE-79\|352 → IPA-WEB-05\|06 (thừa CSRF, vì CWE-352 của bản ghi JVNDB là của CVE khác) |
| CVE-2022-0180 | CWE-352 → IPA-WEB-06 | CWE-79\|352 → IPA-WEB-05\|06 |
| CVE-2021-44228 | CWE-917 → ngoài IPA | CWE-20 → ngoài IPA |

JVN vẫn quý ở chỗ NVD bỏ trống: `CVE-2023-0078` không có CWE trên NVD, JVN cho CWE-79 → IPA-WEB-05.

### 3.5 Dựng KB từ đâu

| Thành phần | File/nguồn | Ai sửa |
|---|---|---|
| Mục IPA (11), đối sách (47) | [`templates/ipa_item.csv`](../templates/ipa_item.csv), [`ipa_countermeasure.csv`](../templates/ipa_countermeasure.csv) | Nhập từ checklist Excel của IPA bằng `import_ipa_checklist.py` (tài liệu 05); bản dịch EN/VI do người viết |
| Mapping IPA↔CWE | [`ipa_cwe_map.csv`](../templates/ipa_cwe_map.csv) | Người biên soạn, duyệt qua PR |
| CWE (tên, cây cha–con view 1000) | XML `cwec_vX.Y.xml` của MITRE | Tự động |
| CWE do JVN gán cho CVE (lấp chỗ trống) | Feed JVN iPedia | Tự động |
| CVE, CWE theo nguồn, trạng thái Rejected | NVD (feed JSON 2.0, API 2.0 hoặc mirror) | Tự động |
| Phiên bản/sha256 từng nguồn | [`templates/source_version.csv`](../templates/source_version.csv) | Ghi khi tải nguồn |

---

## 4 · Công cụ tra cứu vào KB thế nào

| Công cụ | Lấy khóa từ output | Tra file | Khi không thấy |
|---|---|---|---|
| Semgrep | `results[].extra.metadata.cwe` (`"CWE-89: …"`, chuỗi hoặc list) → `CWE-89` | `kb_cwe` | `NO_CWE_INFO` nếu rule không có CWE; `UNKNOWN_CWE` nếu KB không có mã đó |
| ZAP | `site[].alerts[].cweid` (chuỗi số; `-1`/`0` = không có) → `CWE-n` | `kb_cwe` | như trên |
| Trivy, lỗ hổng gói | `VulnerabilityID` (CVE) | `kb_cve` (CWE được chọn) rồi `kb_cwe` (mục IPA) | Không có CVE trong KB → dùng `CweIDs` của Trivy tra `kb_cwe`; CVE bị Rejected → `REJECTED` |
| Trivy, misconfig/secret | không có CWE, không có CVE | — | `NO_CWE_INFO` |

Tùy chọn trước khi tra: sửa CWE sai của rule Semgrep bằng [`tool_side/semgrep_cwe_override.csv`](../tool_side/semgrep_cwe_override.csv) ([tài liệu 02, mục 4.4](02-mapping-semgrep-ipa-va-cap-nhat.md)). Bộ tra cứu ở mục 6.3 không áp bước này, để chỉ dựa vào KB.

**Chạy thật** (`map_findings_to_kb.py` với `kb_cwe.csv`, `kb_cve.sample.csv` và cùng các đầu vào như tài liệu 02 mục 6.2: scan Semgrep thật, 5 golden file của Trivy, fixture ZAP): 58 finding.

| Công cụ | MAPPED | OUT_OF_IPA_SCOPE | NO_CWE_INFO |
|---|---|---|---|
| Semgrep (20) | 9 | 9 | 2 |
| ZAP (6, gồm 2 alert của fixture) | 4 | 0 | 2 |
| Trivy (32) | 3 | 6 | 23 (18 misconfig, 2 secret, 3 mã `GMS-2022-20` không phải CVE) |

KB làm thay đổi kết quả so với khi chỉ dùng CWE có sẵn trong output mẫu của Trivy. Lưu ý: các output mẫu này sinh từ **DB kiểm thử** của dự án Trivy, chứa dữ liệu NVD cũ (`LastModifiedDate` 2021). Trivy chọn CWE theo thứ tự nguồn NVD → Red Hat → các distro → GHSA → … (`AllSourceIDs` trong trivy-db), nên khi dùng DB thật cập nhật, Trivy cũng sẽ ghi CWE hiện tại của NVD. Hai dòng đầu dưới đây là khác biệt do **thời điểm dữ liệu**, không phải do nguồn:

| Gói | CVE | CWE trong output mẫu của Trivy | CWE trong KB (nguồn) | Kết quả |
|---|---|---|---|---|
| `jquery@3.3.9` | CVE-2019-11358 | CWE-79 | CWE-1321 (NVD) | Theo Trivy là IPA-WEB-05 (XSS); theo KB là **ngoài IPA** (prototype pollution). Bộ tra cứu ghi chú "CWE của Trivy khác KB" |
| `libssl`/`libcrypto` | CVE-2019-1551 | CWE-200 | CWE-190 (NVD) | Đều ngoài IPA; vẫn được ghi chú khác |
| `golang.org/x/text` | CVE-2021-38561 | (không có) | CWE-125 (NVD) | KB lấp chỗ trống → IPA-WEB-10 (qua CWE-119) |

---

## 5 · Đo trên dữ liệu NVD thật

Chạy `build_kb_cve.py` trên feed của mirror (không có JVN), tra mục IPA qua `kb_cwe.csv` (mapping seed, CWE 4.14). Không tính CVE `Rejected`.

| | 8 ngày gần nhất (`CVE-Recent`) | Năm 2025 (`CVE-2025`) |
|---|---|---|
| CVE (bỏ Rejected) | 4.856 / 4.998 | 43.640 / 45.429 |
| CWE lấy từ: NVD / CNA-ADP / chỉ mã giả / không có | 0,1% / 75,1% / 0,5% / 24,3% | 12,5% / 83,6% / 2,0% / 1,9% |
| **Khớp mục IPA (MAPPED)** | **35,1%** | **58,8%** |
| … tính trên CVE có CWE thật | 46,7% | 61,2% |
| Ngoài 11 mục IPA | 40,1% | 37,2% |
| Không có thông tin CWE | 24,8% | 3,9% |
| Có KEV / có CVSS v3 / có CVSS v4 | 1 / 3.791 / 1.413 | 189 / 41.347 / 12.477 |
| Các nguồn có CWE khác nhau (`cwe_conflict`) | 2 | 3.335 |

Hai dòng KEV/CVSS và "các nguồn có CWE khác nhau" đo bằng bản KB rộng trước 2026-10-28; bản tối giản không còn các cột đó (số CVE lệch nguồn vẫn được `build_kb_cve.py` in ra). Các dòng còn lại tính lại được từ bản tối giản và cho cùng số.

Năm 2025, chia theo kiểu khớp: `exact` 16.372, `narrower` 2.762, `ancestor` 5.800, `broader` 574, `related` 163. Như vậy khớp "mạnh" (`exact` + `narrower`) là 43,8% số CVE.

Theo mục IPA (2025): XSS 7.815, buffer overflow 5.159, kiểm soát truy cập 4.178, SQLi 3.869, CSRF 1.738, OS command 1.408, path traversal 1.314, quản lý phiên 167, clickjacking 56, HTTP header injection 34, mail header injection 22.

CWE nằm ngoài IPA nhiều nhất (2025): 284 (992), 476 (851), 434 (772), 98 (739), 200 (727), 502 (708), 20 (558), 918 (524), 94 (522), 400 (428).

Cách đọc:

- Feed 8 ngày gần nhất có 24,3% CVE chưa có CWE: CVE mới chưa được CNA/NVD phân tích xong (trạng thái `Awaiting Analysis`, `Received`…). Sau vài tuần tỉ lệ này giảm, nên **`kb_cve` phải sinh lại hằng ngày**.
- 17.278 CVE năm 2025 ở trạng thái `Deferred` và **không CVE nào trong số đó có CWE do NVD gắn**: 16.447 lấy CWE từ CNA/ADP, 831 không có CWE. (Ý nghĩa chính thức của `Deferred` mình chưa đọc được; số liệu là từ dữ liệu thật.)
- Upload file (434) và PHP file inclusion (98) là lỗ hổng web phổ biến nhưng không nằm trong 11 mục. Đây là ứng viên đầu tiên nếu mở rộng bảng IPA.
- Số liệu phụ thuộc bản seed IPA↔CWE và CWE 4.14; đổi mapping thì số đổi theo.

---

## 6 · Code (đã chạy thử)

Python 3.13, chỉ dùng thư viện chuẩn. Các lệnh dưới đây là lệnh đã dùng để sinh file trong `kb/` (thay đường dẫn cho phù hợp):

```bash
python build_kb_cwe.py --cwe-xml cwec_v4.14.xml --ipa-dir templates --out kb/kb_cwe.csv
python build_kb_cve.py --nvd nvd_records/ --jvn jvn/*.rdf --out kb/kb_cve.sample.csv   # thêm --prefer jvn để ưu tiên JVN
python map_findings_to_kb.py kb/kb_cwe.csv kb/kb_cve.sample.csv \
       semgrep=scan.json zap=zap.json trivy=trivy.json out=mapped.csv
```

`--nvd` nhận bản ghi lẻ của repo mirror, feed release (`cve_items`), feed JSON 2.0 chính thức hoặc trang NVD API 2.0 (`vulnerabilities`), hoặc thư mục chứa các file đó. Hai bộ build độc lập nhau: `kb_cve` không cần `kb_cwe`, vì mục IPA được tra lúc dùng.

### 6.1 `build_kb_cwe.py`

<details>
<summary><code>build_kb_cwe.py</code></summary>

```python
"""Dựng KB khóa CWE -> kb_cwe.csv (6 cột): mỗi cặp (CWE, mục IPA) một dòng; CWE không thuộc mục IPA nào vẫn có một dòng."""
import argparse, csv
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

ap = argparse.ArgumentParser()
ap.add_argument("--cwe-xml", required=True)                 # cwec_vX.Y.xml của MITRE
ap.add_argument("--ipa-dir", required=True)                 # có ipa_item.csv, ipa_cwe_map.csv
ap.add_argument("--out", required=True)
a = ap.parse_args()

NS = "{http://cwe.mitre.org/cwe-7}"
root = ET.parse(a.cwe_xml).getroot()
names, parents = {}, defaultdict(list)
for kind in ("Weakness", "Category"):
    for e in root.iter(NS + kind):
        i = int(e.get("ID"))
        names[i] = e.get("Name")
        for r in e.iter(NS + "Related_Weakness"):
            if r.get("Nature") == "ChildOf" and r.get("View_ID") == "1000":
                parents[i].append(int(r.get("CWE_ID")))

def ancestors(i, max_depth):
    """Tổ tiên theo ChildOf (view 1000), gần trước xa sau."""
    seen, q, out = {i}, deque([(i, 0)]), []
    while q:
        c, d = q.popleft()
        if d == max_depth:
            continue
        for p in sorted(parents.get(c, [])):
            if p not in seen:
                seen.add(p); out.append((p, d + 1)); q.append((p, d + 1))
    return out

rd = lambda n: list(csv.DictReader(open(f"{a.ipa_dir}/{n}.csv", encoding="utf-8-sig", newline="")))
items = {r["ipa_id"]: r for r in rd("ipa_item")}
maps = defaultdict(list)
for r in rd("ipa_cwe_map"):
    maps[int(r["cwe_id"])].append(r)

def ipa_rows(i):
    """(ipa_id, match_kind, mapping_status): khớp trực tiếp; nếu CWE chưa có trong bảng thì đi lên cây (chỉ từ dòng exact)."""
    if i in maps:
        return [(m["ipa_id"], m["relation"], m["verification_status"]) for m in maps[i]]
    out, seen = [], set()
    for anc, _ in ancestors(i, 4):
        for m in maps.get(anc, []):
            if m["relation"] == "exact" and m["ipa_id"] not in seen:
                seen.add(m["ipa_id"])
                out.append((m["ipa_id"], "ancestor", m["verification_status"]))
    return out

COLS = ["cwe_id", "cwe_name_en", "ipa_id", "ipa_name_ja", "match_kind", "mapping_status"]
PSEUDO = [("NVD-CWE-Other", "NVD pseudo-CWE: weakness not covered by the CWE slice NVD uses"),
          ("NVD-CWE-noinfo", "NVD pseudo-CWE: insufficient information"),
          ("CWE-noinfo", "JVN iPedia pseudo-CWE: insufficient information")]
with open(a.out, "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo, lineterminator="\n")
    w.writerow(COLS)
    for i in sorted(names):
        for ipa, mk, st in ipa_rows(i) or [("", "", "")]:
            w.writerow([f"CWE-{i}", names[i], ipa, items[ipa]["name_ja"] if ipa else "", mk, st])
    for key, desc in PSEUDO:
        w.writerow([key, desc, "", "", "", ""])
print(f"CWE {root.get('Version')} ({root.get('Date')}): {len(names)} CWE + {len(PSEUDO)} pseudo ids -> {a.out}")
```
</details>

### 6.2 `build_kb_cve.py`

<details>
<summary><code>build_kb_cve.py</code></summary>

```python
"""Dựng KB khóa CVE (NVD + JVN iPedia) -> kb_cve.csv (3 cột): mỗi CVE một dòng, CWE được chọn và nguồn của nó."""
import argparse, csv, glob, json, os, re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--nvd", nargs="*", default=[])     # JSON NVD: bản ghi lẻ, feed release (cve_items) hoặc trang API 2.0; nhận cả thư mục
ap.add_argument("--jvn", nargs="*", default=[])     # feed RDF JVN iPedia (RSS hoặc chi tiết VULDEF)
ap.add_argument("--prefer", choices=["nvd", "jvn"], default="nvd")
ap.add_argument("--out", required=True)
a = ap.parse_args()

REAL = re.compile(r"^CWE-\d+$")
uniq = lambda xs: list(dict.fromkeys(x for x in xs if x))
real = lambda xs: [x for x in xs if REAL.match(x)]

def nvd_records(paths):
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, "**", "*.json"), recursive=True)) if os.path.isdir(p) else [p]
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        if "cve_items" in d:                        # feed release của mirror fkie-cad
            yield from d["cve_items"]
        elif "vulnerabilities" in d:                # trang NVD CVE API 2.0, hoặc feed JSON 2.0 chính thức của NVD
            yield from (v["cve"] for v in d["vulnerabilities"])
        elif "id" in d:                             # một bản ghi lẻ (repo mirror)
            yield d

nvd = {}
for r in nvd_records(a.nvd):
    if (nvd.get(r["id"], {}).get("modified") or "") > (r.get("lastModified") or ""):
        continue                                    # CVE có ở nhiều file (năm, Modified, trang API): giữ bản mới nhất
    by_nvd, other = [], []
    for w in r.get("weaknesses", []):
        (by_nvd if w.get("source") == "nvd@nist.gov" else other).extend(x["value"] for x in w.get("description", []))
    nvd[r["id"]] = dict(modified=r.get("lastModified"), rejected=r.get("vulnStatus") == "Rejected",
                        cwe_nvd=uniq(by_nvd), cwe_other=uniq(other))

# JVN iPedia: một bản ghi JVNDB có thể nêu nhiều CVE; CWE của JVN gắn cho cả bản ghi
SEC, RSS, V = "{http://jvn.jp/rss/mod_sec/}", "{http://purl.org/rss/1.0/}", "{http://jvn.jp/vuldef/}"
jvndb = defaultdict(lambda: dict(cves=[], cwe=[]))
for f in sorted(a.jvn):
    x = ET.parse(f).getroot()
    for it in x.iter(RSS + "item"):                                  # feed RSS (jvnrss 2.0)
        j = jvndb[it.findtext(SEC + "identifier")]
        for ref in it.iter(SEC + "references"):
            rid = (ref.get("id") or "").strip()
            if ref.get("source") in ("CVE", "NVD") and rid.startswith("CVE-"):
                j["cves"].append(rid)
            elif rid.startswith("CWE-"):
                j["cwe"].append(rid)
    for vi in x.iter(V + "Vulinfo"):                                 # feed chi tiết (VULDEF 3.2)
        j = jvndb[vi.findtext(V + "VulinfoID")]
        for ri in vi.find(V + "VulinfoData").iter(V + "RelatedItem"):
            vid = (ri.findtext(V + "VulinfoID") or "").strip()
            if ri.get("type") == "advisory" and vid.startswith("CVE-"):
                j["cves"].append(vid)
            elif ri.get("type") == "cwe" and vid.startswith("CWE-"):
                j["cwe"].append(vid)
jvn = defaultdict(list)
for jid, j in sorted(jvndb.items()):
    for c in uniq(j["cves"]):
        jvn[c] += j["cwe"]

key = lambda c: tuple(int(x) if x.isdigit() else 0 for x in c.split("-")[1:])
stats, disagree = Counter(), 0
with open(a.out, "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo, lineterminator="\n")
    w.writerow(["cve_id", "cwe_selected", "cwe_selected_from"])
    for cve in sorted(set(nvd) | set(jvn), key=key):
        n = nvd.get(cve, {})
        srcs = [("nvd", n.get("cwe_nvd", [])), ("cna_adp", n.get("cwe_other", [])), ("jvn", uniq(jvn.get(cve, [])))]
        if a.prefer == "jvn":
            srcs = [srcs[2], srcs[0], srcs[1]]
        sel, frm = next(((real(l), s) for s, l in srcs if real(l)), (None, None))
        if sel is None:                              # không nguồn nào có CWE thật: giữ mã giả nếu có
            sel, frm = next(((l[:1], "pseudo") for _, l in srcs if l), ([], "none"))
        if n.get("rejected"):                        # NVD đã đánh dấu Rejected: không dùng CWE nào
            sel, frm = [], "rejected"
        else:
            disagree += len({frozenset(real(l)) for _, l in srcs if real(l)}) > 1
        stats[frm] += 1
        w.writerow([cve, "|".join(sel), frm])
print(f"{sum(stats.values())} CVE -> {a.out}; cwe_selected_from {dict(stats.most_common())}; nguồn lệch nhau: {disagree}")
```
</details>

### 6.3 `map_findings_to_kb.py`

<details>
<summary><code>map_findings_to_kb.py</code></summary>

```python
"""Tra output của Semgrep / ZAP / Trivy vào KB IPA + NVD (kb_cwe.csv, kb_cve.csv). Chỉ dùng KB, không dùng rule của công cụ.

python map_findings_to_kb.py kb_cwe.csv kb_cve.csv semgrep=scan.json zap=zap.json trivy=trivy.json [out=mapped.csv]
"""
import csv, json, re, sys
from collections import Counter, defaultdict

kb_cwe_path, kb_cve_path, *args = sys.argv[1:]
args = [a.split("=", 1) for a in args]
kbw = defaultdict(list)
for r in csv.DictReader(open(kb_cwe_path, encoding="utf-8-sig", newline="")):
    kbw[r["cwe_id"]].append(r)
kbv = {r["cve_id"]: r for r in csv.DictReader(open(kb_cve_path, encoding="utf-8-sig", newline=""))}
RANK = {"exact": 5, "narrower": 4, "broader": 3, "ancestor": 2, "related": 1}

def norm(v):
    """'CWE-89: ...' / '89' / 89 / 'CWE-79' -> 'CWE-89'; mã giả giữ nguyên nếu KB có; '-1', '0', '' -> None."""
    s = str(v).strip()
    if s in kbw:
        return s
    m = re.match(r"(?:CWE-)?(\d+)", s, re.I)
    return f"CWE-{int(m[1])}" if m and int(m[1]) > 0 else None

def by_cwe(cwes):
    """Tra danh sách CWE trong kb_cwe -> (ipa_status, ipa_ids, match_kind tốt nhất, mapping_status)."""
    cwes = [c for c in dict.fromkeys(cwes) if c]
    if not cwes:
        return "NO_CWE_INFO", "", "", ""
    known = [c for c in cwes if c in kbw]
    if not known:
        return "UNKNOWN_CWE", "", "", ""             # CWE không có trong KB (bản CWE mới hơn KB, hoặc mã View)
    hits = [r for c in known for r in kbw[c] if r["ipa_id"]]
    if hits:
        return ("MAPPED", "|".join(sorted({r["ipa_id"] for r in hits})), max((r["match_kind"] for r in hits), key=RANK.get),
                "|".join(sorted({r["mapping_status"] for r in hits})))
    return ("OUT_OF_IPA_SCOPE" if any(re.fullmatch(r"CWE-\d+", c) for c in known) else "NO_CWE_INFO"), "", "", ""

COLS = ["tool", "check_id", "location", "lookup", "cwe_used", "cwe_from", "tool_cwe", "ipa_status", "ipa_ids", "match_kind",
        "mapping_status", "note"]
out = []
def emit(tool, check, loc, lookup, cwes, frm, tool_cwe, status, ipa, match, mstatus, note=""):
    out.append([tool, check, loc, lookup, "|".join(c for c in cwes if c), frm, "|".join(c for c in tool_cwe if c), status, ipa,
                match, mstatus, note])

for tool, path in args:
    if tool == "out":
        continue
    d = json.load(open(path, encoding="utf-8"))
    if tool == "semgrep":                         # CWE nằm trong metadata của rule đi kèm finding
        for r in d["results"]:
            raw = r["extra"].get("metadata", {}).get("cwe") or []
            cw = [norm(x) for x in ([raw] if isinstance(raw, str) else raw)]
            emit(tool, r["check_id"].split(".")[-1], f'{r["path"]}:{r["start"]["line"]}', "CWE", cw, "tool", cw, *by_cwe(cw))
    elif tool == "zap":                           # cweid là chuỗi số; -1/0 = không có
        for site in d.get("site", []):
            for al in site.get("alerts", []):
                cw = [norm(al.get("cweid"))]
                for inst in al.get("instances") or [{}]:
                    emit(tool, al.get("pluginid"), inst.get("uri", site.get("@name", "")), "CWE", cw, "tool", cw, *by_cwe(cw))
    elif tool == "trivy":                         # lỗ hổng gói: tra kb_cve theo CVE rồi kb_cwe theo CWE; thiếu CVE mới dùng CWE của Trivy
        for res in d.get("Results", []):
            for v in res.get("Vulnerabilities") or []:
                vid, loc = v["VulnerabilityID"], f'{res["Target"]} :: {v["PkgName"]}@{v.get("InstalledVersion", "")}'
                tcw = [norm(x) for x in v.get("CweIDs") or []]
                row = kbv.get(vid)
                if row and row["cwe_selected_from"] == "rejected":
                    emit(tool, vid, loc, "CVE", [], "kb:rejected", tcw, "REJECTED", "", "", "", note="NVD đã đánh dấu CVE này Rejected")
                elif row:
                    kcw = [c for c in row["cwe_selected"].split("|") if c]
                    note = "CWE của Trivy khác KB" if set(filter(None, tcw)) and set(filter(None, tcw)) != set(kcw) else ""
                    emit(tool, vid, loc, "CVE", kcw, "kb:" + row["cwe_selected_from"], tcw, *by_cwe(kcw), note=note)
                else:
                    emit(tool, vid, loc, "CWE", tcw, "tool", tcw, *by_cwe(tcw), note="CVE không có trong KB")
            for m in res.get("Misconfigurations") or []:
                emit(tool, m["ID"], res["Target"], "-", [], "", [], "NO_CWE_INFO", "", "", "", note="misconfig: không có CWE/CVE")
            for s in res.get("Secrets") or []:
                emit(tool, s["RuleID"], res["Target"], "-", [], "", [], "NO_CWE_INFO", "", "", "", note="secret: không có CWE/CVE")

dest = dict(a for a in args if a[0] == "out").get("out")
w = csv.writer(open(dest, "w", newline="", encoding="utf-8") if dest else sys.stdout, lineterminator="\n")
w.writerow(COLS)
w.writerows(out)
print("tổng:", dict(Counter((r[0], r[7]) for r in out)), file=sys.stderr)
```
</details>

---

## 7 · Cập nhật liên tục

| Nguồn | Phát hiện thay đổi | Tần suất | Việc khi đổi |
|---|---|---|---|
| NVD qua mirror | Tải `CVE-<YEAR>.meta`, so `sha256`/`lastModifiedDate` với `source_version.csv`; chỉ tải lại năm đổi | Mỗi ngày (mirror release 00:00 UTC) | Giải nén, so sha256 với `.meta`, sinh lại `kb_cve.csv` |
| NVD API chính thức | `lastModStartDate`/`lastModEndDate` từ lần chạy trước (khoảng ≤ 120 ngày), có khóa API, chờ giữa các request theo giới hạn **[tìm kiếm web]** | Vài giờ một lần | Ghi đè bản ghi CVE đổi, sinh lại `kb_cve.csv` |
| JVN iPedia | Tải `checksum.txt`, so `sha256` từng feed (RSS theo năm, chi tiết theo năm) | Mỗi ngày | Tải lại feed đổi; sinh lại `kb_cve.csv` |
| CWE (MITRE) | Phiên bản catalog (tài liệu 02 mục 10) | Hằng tuần | Sinh lại `kb_cwe.csv`; kiểm tra CWE trong `ipa_cwe_map` còn tồn tại, không Deprecated |
| IPA (tài liệu hướng dẫn) | Băm nội dung trang/PDF và file checklist Excel (tài liệu 02 mục 10) | Hằng tuần | Checklist mới: chạy `import_ipa_checklist.py` (tài liệu 05) cho `ipa_countermeasure.csv`, người đối chiếu `ipa_item.csv` và `ipa_cwe_map.csv`, rồi sinh lại `kb_cwe.csv` |

Nguyên tắc:

- **`kb_cwe.csv` commit vào git**: nhỏ, xác định từng byte. Mỗi PR cập nhật cho thấy đúng dòng nào đổi, người duyệt nhìn được mapping IPA thay đổi ra sao. Thay đổi từ IPA không tự merge.
- **`kb_cve.csv` không commit**: lớn và đổi mỗi ngày. Sinh trong CI hoặc job, nạp vào DB hoặc lưu thành artifact có kèm `source_version.csv`. Báo cáo scan ghi phiên bản KB đã dùng.
- **Kiểm tra trước khi phát hành** (`check_kb.py`, tài liệu 05): đúng tên cột; sha256 khớp `.meta`; không trùng `cve_id`; `cwe_selected` khớp với `cwe_selected_from`; số CVE không giảm (CVE bị Rejected vẫn ở lại với `rejected`); tỉ lệ CVE vào mục IPA không lệch quá 2 điểm so với lần trước; cảnh báo khi còn mapping IPA chưa duyệt.
- **Không phụ thuộc host bị chặn**: nếu NVD hoặc JVN tạm không truy cập được, dùng bản KB gần nhất và đánh dấu `error` trong `source_version.csv`.
- **Cùng một CVE có ở nhiều file** (feed năm, feed Modified, trang API): `build_kb_cve.py` giữ bản có `lastModified` mới nhất, không phụ thuộc thứ tự file.
- **Các bước cụ thể và script đã chạy thử** (đồng bộ feed có kiểm tra sha256, client NVD API, kiểm tra trước khi phát hành, job hằng ngày): [tài liệu 05, tiếng Anh](05-kb-build-runbook.md).

---

## 8 · Giới hạn, việc cần người, bước tiếp

**Giới hạn của bản hiện tại**

- Mapping IPA↔CWE là **seed chưa xác minh**; mọi số liệu IPA ở trên phụ thuộc bản seed này.
- CWE 4.14 (2024-02-29) đã cũ; view 1003 và cây CWE có thể đã đổi ở bản mới.
- Dữ liệu JVN là fixture snapshot 2023-11-02, chỉ 13 bản ghi, nên gần như không CVE nào lấy CWE từ JVN.
- Mã giả `CWE-Other` của JVN (nếu có) chưa thấy trong dữ liệu nên chưa có dòng trong `kb_cwe`; nếu công cụ gặp mã này sẽ ra `UNKNOWN_CWE`.
- Chưa chạy Trivy/ZAP thật (tài liệu 02 mục 11).
- Điều khoản sử dụng dữ liệu NVD, JVN iPedia và mirror chưa được đọc **[chưa xác minh]**.

**Việc cần người**

1. Mở host `services.nvd.nist.gov`, `jvndb.jvn.jp`, `www.ipa.go.jp` (hoặc dùng mirror và đồng ý điều khoản), để KB lấy dữ liệu trực tiếp thay vì qua mirror/fixture.
2. Người đọc tiếng Nhật đối chiếu bảng IPA↔CWE với tài liệu gốc của IPA và JVN iPedia, rồi nâng `mapping_status` lên `verified` (checklist Excel bản 7 đã xác nhận 11 mục và 47 đối sách, nhưng không có mã CWE).
3. Chọn chính sách CWE cho CVE: giữ mặc định NVD → CNA/ADP → JVN, hay ưu tiên JVN.
4. Quyết định có mở rộng mục IPA cho CWE-434, 98, 918, 502 (nhiều CVE nhưng ngoài 11 mục) hay không.

**Bước tiếp**

1. Tải toàn bộ feed JVN theo năm, sinh lại `kb_cve.csv` để JVN lấp CWE cho các CVE mà NVD/CNA bỏ trống.
2. Tải CWE mới nhất, sinh lại `kb_cwe.csv`, so view 1003 cũ/mới.
3. Dựng job hằng ngày sinh `kb_cve.csv` cho toàn bộ NVD, kèm các kiểm tra ở mục 7.
4. Chạy Semgrep/ZAP/Trivy thật trên một ứng dụng thử nghiệm, tra vào KB và xem lại các finding mà CWE của công cụ khác KB.

---

## 9 · Nguồn

Đã đọc trực tiếp / chạy thật trong phiên:

- Mirror NVD [`fkie-cad/nvd-json-data-feeds`](https://github.com/fkie-cad/nvd-json-data-feeds): README, 23 bản ghi CVE lẻ, release `CVE-Recent.json.xz` và `CVE-2025.json.xz` cùng file `.meta` (sha256 đã đối chiếu).
- [`vulsio/go-cve-dictionary`](https://github.com/vulsio/go-cve-dictionary) commit `d1af699` (2026-10-02): mã tải NVD/JVN, URL feed JVN.
- [`MaineK00n/vuls-data-update`](https://github.com/MaineK00n/vuls-data-update) commit `969aa0a` (2026-10-26): kiểu dữ liệu và fixture thật của feed RSS/chi tiết JVN iPedia, `checksum.txt`.
- Dữ liệu CWE 4.14 (gói PyPI `cwe2`): view 1000, view 1003.
- Các template IPA trong `templates/`.
- Checklist Excel 安全なウェブサイトの作り方 改訂第7版 của IPA ([000044403.xlsx](https://www.ipa.go.jp/security/vuln/websecurity/ug65p900000196e2-att/000044403.xlsx)), do người dùng cung cấp: 11 mục, 47 đối sách.

Chỉ qua kết quả WebSearch:

- NVD CVE API 2.0 (tham số, giới hạn): <https://nvd.nist.gov/developers/vulnerabilities>, <https://nvd.nist.gov/developers/api-workflows>, [nvdlib](https://nvdlibdocs.readthedocs.io/en/latest/_modules/nvdlib/cve.html)
- MyJVN API: <https://jvndb.jvn.jp/en/apis/>, [go-myjvn](https://beta.pkg.go.dev/github.com/spiegel-im-spiegel/go-myjvn), [Hitachi HIRT](https://www.hitachi.com/ja-jp/hirt/publications/hirt-pub/hirt-pub14009/)
- Feed JVN iPedia: <https://jvndb.jvn.jp/en/feed>, <https://jvndb.jvn.jp/en/schema/jvnrss.html>
