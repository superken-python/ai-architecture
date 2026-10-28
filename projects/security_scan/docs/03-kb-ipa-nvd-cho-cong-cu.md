# 03 · Knowledge base IPA + NVD để Semgrep, ZAP, Trivy tra cứu

Ngày: 2026-10-27 · Đọc cùng: [01 · Nghiên cứu IPA, CWE, Semgrep](01-nghien-cuu-ipa-cwe-semgrep.md), [02 · Phía công cụ](02-mapping-semgrep-ipa-va-cap-nhat.md). Nhãn nguồn dùng như tài liệu 01: **[đã kiểm chứng]** (mình tự chạy/đọc dữ liệu thật), **[tìm kiếm web]** (đoạn trích, chưa đọc trang gốc), **[chưa xác minh]**.

## 0 · Đính chính hướng thiết kế

Lần trước mình làm ngược: lấy rule của Semgrep/ZAP đổ vào template (`exports/ipa_map_all_tools.csv`, đã gỡ). Đúng ra **IPA và NVD là tài liệu tham chiếu**. Cần export dữ liệu tổng hợp của IPA + NVD thành một knowledge base (KB), rồi các công cụ chỉ đưa ra *khóa* (CWE, CVE) để tra vào KB đó.

```
 Semgrep ─┐ CWE                 ┌──────────────── KB IPA + NVD (không phụ thuộc công cụ) ─────────────────┐
 ZAP ─────┼────────────────────►│ kb_cwe.csv : CWE → tên EN/JA, CWE mà NVD dùng, mục IPA, đối sách IPA     │
 Trivy ───┘ CVE ───────────────►│ kb_cve.csv : CVE → CWE theo từng nguồn (NVD, CNA/ADP, JVN), CWE được chọn │
            (CWE của Trivy chỉ  │              → mục IPA; CVSS, KEV, mã JVNDB, tiêu đề tiếng Nhật          │
             dùng khi KB thiếu) └─────▲───────────────────────▲─────────────────────────▲───────────────────┘
                                      │ MITRE CWE             │ NVD: CVE JSON 2.0        │ IPA: 安全なウェブサイトの作り方
                                      │ (view 1000, 1003)     │ (API hoặc mirror)        │      + JVN iPedia (JVNDB)
```

Dữ liệu rule của công cụ (catalog rule, override CWE sai của rule) chuyển sang thư mục [`tool_side/`](../tool_side/). Đó là việc chuẩn hóa *trước khi* tra KB, không phải nội dung KB ([tài liệu 02](02-mapping-semgrep-ipa-va-cap-nhat.md)).

## 1 · Tóm tắt

1. **KB gồm hai file theo hai khóa**: [`kb/kb_cwe.csv`](../kb/kb_cwe.csv) (khóa CWE, cho Semgrep, ZAP và Trivy) và `kb_cve.csv` (khóa CVE, cho Trivy). Mỗi công cụ chỉ cần tra một file. Không gộp làm một vì NVD có hơn 415.000 CVE cập nhật mỗi ngày, còn phần CWE + IPA nhỏ và đổi chậm.
2. **Đã dựng thật**: `kb_cwe.csv` đầy đủ (1.375 khóa: 963 weakness, 409 category, 3 mã giả của NVD/JVN) và [`kb/kb_cve.sample.csv`](../kb/kb_cve.sample.csv) (23 CVE thật, ghép NVD với JVN iPedia). Bản `kb_cve` đầy đủ sinh bằng script ở mục 6. Chạy cho cả năm 2025 (45.429 CVE) mất khoảng 11 giây.
3. **Một CVE có thể mang CWE khác nhau tùy nguồn và tùy thời điểm**, nên KB lưu CWE của **từng nguồn** rồi mới chọn. Ví dụ thật: Log4Shell có JVN = 20, CNA = 20/400/502, NVD = 917. Với jquery `CVE-2019-11358`, NVD hiện ghi CWE-1321, GHSA ghi cả 1321 lẫn 79, còn DB kiểm thử của Trivy (chụp dữ liệu NVD năm 2021) ghi CWE-79: cùng nguồn NVD nhưng khác thời điểm (xem [tài liệu 04](04-thuat-ngu-so-sanh-va-cach-map.md)).
4. **JVN iPedia (của IPA) gắn CWE cho cả bản ghi JVNDB**, có thể chứa nhiều CVE. Lấy CWE của JVN làm mặc định sẽ làm phình mapping, nên mặc định ưu tiên NVD rồi CNA/ADP, và JVN để lấp chỗ trống (`--prefer jvn` để đảo thứ tự).
5. **NVD tự gắn CWE cho rất ít CVE mới**: năm 2025 chỉ 12,5% CWE do chính NVD gắn, 83,6% do CNA/ADP. KB nào chỉ lấy CWE `nvd@nist.gov` sẽ mất phần lớn dữ liệu.
6. **Độ phủ của 11 mục IPA trên CVE thật cao hơn nhiều so với trên rule công cụ**: năm 2025 có **58,8%** CVE (không tính Rejected) rơi vào một mục IPA. Trên rule của Semgrep/ZAP con số này chỉ khoảng 25% (tài liệu 02). Phần ngoài IPA lớn nhất: CWE-284, 476, **434 (upload file)**, **98 (PHP file inclusion)**, 200, 502.
7. **Tên CWE tiếng Nhật do IPA dùng** lấy được từ chính feed JVN iPedia (ví dụ `クロスサイトスクリプティング`), kèm link trang CWE của JVN.
8. **Cập nhật liên tục có sẵn cơ chế kiểm tra**: mirror NVD có file `.meta` chứa sha256 (đã đối chiếu khớp), JVN iPedia có `checksum.txt` liệt kê sha256 của mọi feed.
9. **Giới hạn**: `services.nvd.nist.gov`, `jvndb.jvn.jp`, `www.ipa.go.jp` bị chặn trong môi trường này. Dữ liệu NVD lấy qua mirror `fkie-cad/nvd-json-data-feeds` (snapshot 2026-10-27). Dữ liệu JVN lấy từ fixture thật trong repo `vuls-data-update` (snapshot 2023-11-02). Mapping CWE↔IPA vẫn là bản seed **chưa xác minh**.

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

**Tên CWE tiếng Nhật thu được từ dữ liệu thật** (đã đưa vào `kb_cwe.csv`; template `cwe_catalog.csv` có 5 tên trong số này vì bản mẫu chỉ chứa một phần CWE): CWE-20 不適切な入力確認, CWE-79 クロスサイトスクリプティング, CWE-89 SQLインジェクション, CWE-94 コード・インジェクション, CWE-352 クロスサイトリクエストフォージェリ, CWE-399 リソース管理の問題, CWE-476 NULL ポインタデリファレンス, CWE-640 パスワードを忘れた場合の脆弱なパスワードリカバリの仕組み, mã giả `CWE-noinfo` 情報不足. Tên đầy đủ cho mọi CWE cần đọc toàn bộ feed theo năm. Lưu ý tên của JVN có thể khác cách viết trong tài liệu hướng dẫn của IPA (ví dụ `クロスサイト・スクリプティング` có dấu `・`).

Ghi chú khi dùng: `go-cve-dictionary` bỏ các mục mà phần mô tả chứa `** 未確定 **`, `** サポート外 **` hoặc `** 削除 **`. Bộ build ở mục 6 chưa lọc các mục này (fixture không có mục nào như vậy để thử).

### 2.3 IPA: 安全なウェブサイトの作り方

Giữ nguyên như tài liệu [01](01-nghien-cuu-ipa-cwe-semgrep.md) và [02](02-mapping-semgrep-ipa-va-cap-nhat.md): 11 mục, đối sách gốc rễ/bảo hiểm, bảng IPA↔CWE. Các nội dung này là **seed theo trí nhớ, chưa xác minh** (`templates/ipa_item.csv`, `ipa_cwe_map.csv`, `ipa_countermeasure.csv`).

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

### 3.1 Hai file, hai khóa

| File | Khóa | Công cụ dùng | Cỡ | Đổi khi nào |
|---|---|---|---|---|
| [`kb/kb_cwe.csv`](../kb/kb_cwe.csv) | `cwe_id` dạng `CWE-79` (cả mã giả `NVD-CWE-noinfo`, `NVD-CWE-Other`, `CWE-noinfo`) | Semgrep, ZAP, Trivy (khi chỉ có CWE) | 1.376 dòng, khoảng 190 KB; **đầy đủ** | Khi CWE, mapping IPA hoặc tên tiếng Nhật đổi: vài lần mỗi năm, duyệt qua PR |
| `kb_cve.csv` | `cve_id` | Trivy (và mọi công cụ báo CVE) | khoảng 415.000 dòng; năm 2025 riêng đã 33 MB | Mỗi ngày; sinh lại bằng script, không commit |
| [`kb/kb_cve.sample.csv`](../kb/kb_cve.sample.csv) | `cve_id` | Mẫu | 23 CVE thật | Mẫu cột và dữ liệu, không phải bản đầy đủ |

Mỗi ô một dòng (đã chuẩn hóa xuống dòng trong mô tả), UTF-8, dấu phẩy, danh sách trong ô ngăn bằng `|`, không có ngày giờ sinh file. Nhờ vậy sinh lại cho cùng dữ liệu thì ra đúng từng byte.

### 3.2 `kb_cwe.csv`: một dòng cho mỗi (CWE, mục IPA)

CWE không thuộc mục IPA nào vẫn có một dòng, với `ipa_status = OUT_OF_IPA_SCOPE`, để công cụ tra mã nào cũng thấy.

| Cột | Ý nghĩa | Nguồn |
|---|---|---|
| `cwe_id`, `cwe_number`, `cwe_kind` | `CWE-79`, 79, `Weakness`/`Category`/`Pseudo` | MITRE |
| `cwe_name_en`, `cwe_abstraction`, `cwe_status` | Tên, mức trừu tượng, trạng thái (`Stable`, `Deprecated`...) | MITRE |
| `cwe_name_ja`, `jvn_cwe_url` | Tên tiếng Nhật và trang CWE của JVN, nếu đã thấy trong feed | IPA (JVN iPedia) |
| `cwe_parent_ids` | Cha theo view 1000, ví dụ `CWE-943` | MITRE |
| `nvd_slice` | `Y` nếu CWE thuộc view 1003 (tập NVD dùng) | MITRE/NVD |
| `nvd_slice_cwe_id` | CWE gần nhất thuộc view 1003, đi theo chuỗi cha *Primary* (CWE-113 → 93 → **74**); rỗng nếu chuỗi cha không gặp (khi đó NVD thường ghi `NVD-CWE-Other`) | MITRE/NVD |
| `ipa_status` | `MAPPED`, `OUT_OF_IPA_SCOPE`, `NO_CWE_INFO` (mã giả) | Tính |
| `ipa_id`, `ipa_section_no`, `ipa_name_ja`, `ipa_name_en`, `ipa_name_vi` | Mục IPA | IPA |
| `match_kind`, `via_cwe_id`, `confidence` | `exact`/`narrower`/`broader`/`related` (trực tiếp từ `ipa_cwe_map`) hoặc `ancestor` (qua tổ tiên ≤ 4 cấp, `via_cwe_id` là tổ tiên đã khớp) | IPA + MITRE |
| `mapping_status` | Trạng thái duyệt của dòng mapping (hiện mọi dòng `seed_unverified`) | IPA |
| `ipa_measure_ids` | Mã đối sách của mục IPA, gốc rễ trước; nối với `templates/ipa_countermeasure.csv` | IPA |
| `cwe_version` | Phiên bản CWE (4.14) | MITRE |

Bản hiện tại: 1.375 khóa CWE, 102 CWE map được vào mục IPA (103 dòng vì CWE-93 thuộc cả 1.7 và 1.8), 1.270 dòng `OUT_OF_IPA_SCOPE`, 3 dòng mã giả.

### 3.3 `kb_cve.csv`: một dòng cho mỗi CVE

| Nhóm | Cột |
|---|---|
| NVD | `cve_id`, `nvd_url`, `nvd_vuln_status`, `nvd_published`, `nvd_last_modified`, `nvd_source_identifier`, `nvd_description_en` |
| CWE theo nguồn | `cwe_nvd` (do `nvd@nist.gov` gắn, có thể là mã giả), `cwe_cna_adp` và `cwe_cna_adp_sources` (CNA, ADP), `cwe_jvn` (JVN iPedia, theo bản ghi JVNDB) |
| CWE được chọn | `cwe_selected`, `cwe_selected_from` (`nvd`, `cna_adp`, `jvn`, `pseudo`, `none`), `cwe_conflict` (`Y` khi các nguồn có CWE thật nhưng khác nhau) |
| IPA | `ipa_status`, `ipa_ids` (từ CWE được chọn, tra qua `kb_cwe`), `ipa_best_match`, `ipa_ids_any_source` (mục IPA mà CWE của *bất kỳ* nguồn nào dẫn tới, để thấy chỗ lệch) |
| Mức nghiêm trọng | `cvss_v3_score/severity/vector/source` (3.1 trước, rồi 3.0; ưu tiên `nvd@nist.gov` loại Primary), `cvss_v4_*`, `kev_date_added`, `kev_due_date`, `kev_name` |
| JVN iPedia | `jvndb_ids`, `jvn_title_ja`, `jvn_cvss_v3_score`, `jvn_cvss_v3_severity` (do IPA chấm), `jvn_last_updated`, `jvn_url` |

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
| Mục IPA, đối sách, mapping IPA↔CWE | [`templates/ipa_item.csv`](../templates/ipa_item.csv), [`ipa_countermeasure.csv`](../templates/ipa_countermeasure.csv), [`ipa_cwe_map.csv`](../templates/ipa_cwe_map.csv) | Người biên soạn, duyệt qua PR |
| CWE (tên, cây, view 1003) | XML `cwec_vX.Y.xml` của MITRE | Tự động |
| Tên CWE tiếng Nhật, JVNDB ↔ CVE, CWE và CVSS do IPA gán | Feed JVN iPedia | Tự động |
| CVE, CWE theo nguồn, CVSS, KEV | NVD API 2.0 hoặc mirror | Tự động |
| Phiên bản/sha256 từng nguồn | [`templates/source_version.csv`](../templates/source_version.csv) | Tự động |

---

## 4 · Công cụ tra cứu vào KB thế nào

| Công cụ | Lấy khóa từ output | Tra file | Khi không thấy |
|---|---|---|---|
| Semgrep | `results[].extra.metadata.cwe` (`"CWE-89: …"`, chuỗi hoặc list) → `CWE-89` | `kb_cwe` | `NO_CWE_INFO` nếu rule không có CWE; `UNKNOWN_CWE` nếu KB không có mã đó |
| ZAP | `site[].alerts[].cweid` (chuỗi số; `-1`/`0` = không có) → `CWE-n` | `kb_cwe` | như trên |
| Trivy, lỗ hổng gói | `VulnerabilityID` (CVE) | `kb_cve` (CWE được chọn, mục IPA, CVSS, KEV, JVNDB) | Không có CVE trong KB → dùng `CweIDs` của Trivy tra `kb_cwe` |
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
python build_kb_cwe.py --cwe-xml cwec_v4.14.xml --ipa-dir templates \
       --jvn jvn/*.rdf --out kb/kb_cwe.csv
python build_kb_cve.py --nvd nvd_records/ --jvn jvn/*.rdf \
       --kb-cwe kb/kb_cwe.csv --out kb/kb_cve.sample.csv            # thêm --prefer jvn để ưu tiên JVN
python map_findings_to_kb.py kb/kb_cwe.csv kb/kb_cve.sample.csv \
       semgrep=scan.json zap=zap.json trivy=trivy.json out=mapped.csv
```

`--nvd` nhận bản ghi lẻ của repo mirror, feed release (`cve_items`), trang kết quả NVD API 2.0 (`vulnerabilities`) hoặc thư mục chứa các file đó.

### 6.1 `build_kb_cwe.py`

<details>
<summary><code>build_kb_cwe.py</code></summary>

```python
"""Dựng KB khóa CWE (IPA + NVD) -> kb_cwe.csv: mỗi CWE (kể cả mã giả) đủ thông tin để công cụ tra cứu."""
import argparse, csv, re
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

ap = argparse.ArgumentParser()
ap.add_argument("--cwe-xml", required=True)                 # cwec_vX.Y.xml của MITRE
ap.add_argument("--ipa-dir", required=True)                 # có ipa_item.csv, ipa_cwe_map.csv, ipa_countermeasure.csv
ap.add_argument("--jvn", nargs="*", default=[])             # feed RDF JVN iPedia (RSS hoặc chi tiết) -> tên CWE tiếng Nhật
ap.add_argument("--out", required=True)
a = ap.parse_args()

NS = "{http://cwe.mitre.org/cwe-7}"
root = ET.parse(a.cwe_xml).getroot()
cwe, parents, primary, nvd_slice = {}, defaultdict(list), {}, set()
for kind in ("Weakness", "Category"):
    for e in root.iter(NS + kind):
        i = int(e.get("ID"))
        cwe[i] = dict(kind=kind, name=e.get("Name"), abs=e.get("Abstraction") or "", status=e.get("Status"))
        for r in e.iter(NS + "Related_Weakness"):
            if r.get("Nature") == "ChildOf" and r.get("View_ID") == "1000":
                parents[i].append(int(r.get("CWE_ID")))
                if r.get("Ordinal") == "Primary":
                    primary[i] = int(r.get("CWE_ID"))     # mỗi weakness có đúng một cha Primary
            if r.get("Nature") == "ChildOf" and r.get("View_ID") == "1003":
                nvd_slice.add(i)                            # nút con trong view 1003
for v in root.iter(NS + "View"):
    if v.get("ID") == "1003":                               # view NVD dùng để gắn CWE cho CVE
        nvd_slice |= {int(m.get("CWE_ID")) for m in v.iter(NS + "Has_Member")}

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

# Tên CWE tiếng Nhật do IPA dùng trong JVN iPedia
ja, ja_url = {}, {}
def put(cid, title, url):
    cid = (cid or "").strip()
    if cid.startswith("CWE-") and title:
        ja.setdefault(cid, re.sub(r"\s*\(CWE-[^)]*\)\s*$", "", title.strip()))
        if url and "jvndb.jvn.jp" in url:
            ja_url.setdefault(cid, url.strip())
for f in sorted(a.jvn):
    x = ET.parse(f).getroot()
    for ref in x.iter("{http://jvn.jp/rss/mod_sec/}references"):             # feed RSS (jvnrss 2.0)
        put(ref.get("id"), ref.get("title"), ref.text)
    for it in x.iter("{http://jvn.jp/vuldef/}RelatedItem"):                  # feed chi tiết (VULDEF 3.2)
        if it.get("type") == "cwe":
            put(it.findtext("{http://jvn.jp/vuldef/}VulinfoID"), it.findtext("{http://jvn.jp/vuldef/}Title"),
                it.findtext("{http://jvn.jp/vuldef/}URL"))

rd = lambda n: list(csv.DictReader(open(f"{a.ipa_dir}/{n}.csv", encoding="utf-8-sig", newline="")))
items = {r["ipa_id"]: r for r in rd("ipa_item")}
maps = defaultdict(list)
for r in rd("ipa_cwe_map"):
    maps[int(r["cwe_id"])].append(r)
measures = defaultdict(list)
for r in sorted(rd("ipa_countermeasure"), key=lambda r: (r["measure_type"] != "root_cause", r["measure_id"])):
    measures[r["ipa_id"]].append(r["measure_id"])

def ipa_rows(i):
    """(ipa_id, match_kind, via, confidence, status): khớp trực tiếp; nếu CWE chưa có trong bảng thì đi lên cây."""
    if i in maps:
        return [(m["ipa_id"], m["relation"], "", m["confidence"], m["verification_status"]) for m in maps[i]]
    out, seen = [], set()
    for anc, _ in ancestors(i, 4):
        for m in maps.get(anc, []):
            if m["relation"] == "exact" and m["ipa_id"] not in seen:
                seen.add(m["ipa_id"])
                out.append((m["ipa_id"], "ancestor", f"CWE-{anc}", m["confidence"], m["verification_status"]))
    return out

def nearest_slice(i):
    """CWE gần nhất thuộc tập NVD dùng, đi theo chuỗi cha Primary (113 -> 93 -> 74)."""
    seen = set()
    while i not in seen:
        if i in nvd_slice:
            return f"CWE-{i}"
        seen.add(i)
        if i not in primary:
            break
        i = primary[i]
    return ""

COLS = ("cwe_id,cwe_number,cwe_kind,cwe_name_en,cwe_name_ja,jvn_cwe_url,cwe_abstraction,cwe_status,cwe_parent_ids,"
        "nvd_slice,nvd_slice_cwe_id,ipa_status,ipa_id,ipa_section_no,ipa_name_ja,ipa_name_en,ipa_name_vi,match_kind,"
        "via_cwe_id,confidence,mapping_status,ipa_measure_ids,cwe_version").split(",")
PSEUDO = [("NVD-CWE-Other", "NVD pseudo-CWE: weakness not covered by the CWE slice NVD uses"),
          ("NVD-CWE-noinfo", "NVD pseudo-CWE: insufficient information"),
          ("CWE-noinfo", "JVN iPedia pseudo-CWE: insufficient information")]
with open(a.out, "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo, lineterminator="\n")
    w.writerow(COLS)
    ver = root.get("Version")
    for i in sorted(cwe):
        c, key = cwe[i], f"CWE-{i}"
        base = [key, i, c["kind"], c["name"], ja.get(key, ""), ja_url.get(key, ""), c["abs"], c["status"],
                "|".join(f"CWE-{p}" for p in sorted(parents.get(i, []))), "Y" if i in nvd_slice else "N", nearest_slice(i)]
        rows = ipa_rows(i)
        if not rows:
            w.writerow(base + ["OUT_OF_IPA_SCOPE"] + [""] * 10 + [ver])
        for ipa, mk, via, conf, st in rows:
            it = items[ipa]
            w.writerow(base + ["MAPPED", ipa, it["section_no"], it["name_ja"], it["name_en"], it["name_vi"], mk, via, conf, st,
                               "|".join(measures.get(ipa, [])), ver])
    for key, desc in PSEUDO:
        w.writerow([key, "", "Pseudo", desc, ja.get(key, ""), ja_url.get(key, ""), "", "", "", "N", "", "NO_CWE_INFO"]
                   + [""] * 10 + [ver])
```
</details>

### 6.2 `build_kb_cve.py`

<details>
<summary><code>build_kb_cve.py</code></summary>

```python
"""Dựng KB khóa CVE (NVD + JVN iPedia) -> kb_cve.csv: mỗi CVE một dòng, CWE theo từng nguồn, CWE được chọn, mục IPA."""
import argparse, csv, glob, json, os, re
import xml.etree.ElementTree as ET
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--nvd", nargs="*", default=[])     # JSON NVD: bản ghi lẻ, feed release (cve_items) hoặc trang API 2.0; nhận cả thư mục
ap.add_argument("--jvn", nargs="*", default=[])     # feed RDF JVN iPedia (RSS hoặc chi tiết VULDEF)
ap.add_argument("--kb-cwe", required=True)          # kb_cwe.csv đã dựng
ap.add_argument("--prefer", choices=["nvd", "jvn"], default="nvd")
ap.add_argument("--out", required=True)
a = ap.parse_args()

REAL = re.compile(r"^CWE-\d+$")
uniq = lambda xs: list(dict.fromkeys(x for x in xs if x))
one_line = lambda t: " ".join((t or "").split())       # mỗi ô CSV một dòng, dễ import
real = lambda xs: [x for x in xs if REAL.match(x)]

def nvd_records(paths):
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, "**", "*.json"), recursive=True)) if os.path.isdir(p) else [p]
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        if "cve_items" in d:                        # feed release của mirror fkie-cad
            yield from d["cve_items"]
        elif "vulnerabilities" in d:                # trang kết quả NVD CVE API 2.0
            yield from (v["cve"] for v in d["vulnerabilities"])
        elif "id" in d:                             # một bản ghi lẻ (repo mirror)
            yield d

def cvss(metrics, keys):
    """Bản CVSS ưu tiên: phiên bản mới nhất có mặt, rồi nguồn nvd@nist.gov loại Primary."""
    for k in keys:
        if metrics.get(k):
            m = sorted(metrics[k], key=lambda m: (m.get("source") != "nvd@nist.gov", m.get("type") != "Primary"))[0]
            c = m["cvssData"]
            return [c.get("baseScore"), c.get("baseSeverity") or m.get("baseSeverity"), c.get("vectorString"), m.get("source")]
    return ["", "", "", ""]

nvd = {}
for r in nvd_records(a.nvd):
    if (nvd.get(r["id"], {}).get("modified") or "") > (r.get("lastModified") or ""):
        continue                                    # CVE có ở nhiều file (năm, Modified, trang API): giữ bản mới nhất
    by_nvd, other, other_src = [], [], []
    for w in r.get("weaknesses", []):
        vals = [x["value"] for x in w.get("description", [])]
        if w.get("source") == "nvd@nist.gov":
            by_nvd += vals
        else:
            other += vals
            other_src.append(w.get("source"))
    m = r.get("metrics", {})
    nvd[r["id"]] = dict(
        status=r.get("vulnStatus"), published=r.get("published"), modified=r.get("lastModified"),
        cna=r.get("sourceIdentifier"), cwe_nvd=uniq(by_nvd), cwe_other=uniq(other), other_src=uniq(other_src),
        v3=cvss(m, ["cvssMetricV31", "cvssMetricV30"]), v4=cvss(m, ["cvssMetricV40"]),
        kev=[r.get("cisaExploitAdd", ""), r.get("cisaActionDue", ""), r.get("cisaVulnerabilityName", "")],
        desc=one_line(next((x["value"] for x in r.get("descriptions", []) if x.get("lang") == "en"), "")))

# JVN iPedia: một bản ghi JVNDB có thể nêu nhiều CVE; CWE của JVN gắn cho cả bản ghi
SEC, RSS, DC, V = ("{http://jvn.jp/rss/mod_sec/}", "{http://purl.org/rss/1.0/}", "{http://purl.org/dc/terms/}",
                   "{http://jvn.jp/vuldef/}")
jvndb = {}
def rec(jid):
    return jvndb.setdefault(jid, dict(cves=[], cwe=[], title="", cvss3=["", ""], updated="", url=""))
for f in sorted(a.jvn):
    x = ET.parse(f).getroot()
    for it in x.iter(RSS + "item"):                                  # feed RSS (jvnrss 2.0)
        j = rec(it.findtext(SEC + "identifier"))
        j["title"] = j["title"] or one_line(it.findtext(RSS + "title"))
        j["url"] = j["url"] or it.findtext(RSS + "link") or ""
        j["updated"] = max(j["updated"], it.findtext(DC + "modified") or "")
        for ref in it.iter(SEC + "references"):
            rid = (ref.get("id") or "").strip()
            if ref.get("source") in ("CVE", "NVD") and rid.startswith("CVE-"):
                j["cves"].append(rid)
            elif rid.startswith("CWE-"):
                j["cwe"].append(rid)
        for c in it.iter(SEC + "cvss"):
            if c.get("version", "").startswith("3"):
                j["cvss3"] = [c.get("score"), c.get("severity")]
    for vi in x.iter(V + "Vulinfo"):                                 # feed chi tiết (VULDEF 3.2)
        j, d = rec(vi.findtext(V + "VulinfoID")), vi.find(V + "VulinfoData")
        j["title"] = j["title"] or one_line(d.findtext(V + "Title"))
        j["updated"] = max(j["updated"], d.findtext(V + "DateLastUpdated") or "")
        for ri in d.iter(V + "RelatedItem"):
            vid = (ri.findtext(V + "VulinfoID") or "").strip()
            if ri.get("type") == "advisory" and vid.startswith("CVE-"):
                j["cves"].append(vid)
            elif ri.get("type") == "cwe" and vid.startswith("CWE-"):
                j["cwe"].append(vid)
        for c in d.iter(V + "Cvss"):
            if c.get("version", "").startswith("3"):
                j["cvss3"] = [c.findtext(V + "Base"), c.findtext(V + "Severity")]
jvn = defaultdict(list)
for jid, j in sorted(jvndb.items()):
    if not j["url"]:
        j["url"] = f"https://jvndb.jvn.jp/ja/contents/{jid.split('-')[1]}/{jid}.html"
    for c in uniq(j["cves"]):
        jvn[c].append((jid, j))

kb = defaultdict(list)
for r in csv.DictReader(open(a.kb_cwe, encoding="utf-8-sig", newline="")):
    if r["ipa_status"] == "MAPPED":
        kb[r["cwe_id"]].append((r["ipa_id"], r["match_kind"]))
RANK = {"exact": 5, "narrower": 4, "broader": 3, "ancestor": 2, "related": 1}

COLS = ("cve_id,nvd_url,nvd_vuln_status,nvd_published,nvd_last_modified,nvd_source_identifier,cwe_nvd,cwe_cna_adp,"
        "cwe_cna_adp_sources,cwe_jvn,cwe_selected,cwe_selected_from,cwe_conflict,ipa_status,ipa_ids,ipa_best_match,"
        "ipa_ids_any_source,cvss_v3_score,cvss_v3_severity,cvss_v3_vector,cvss_v3_source,cvss_v4_score,cvss_v4_severity,"
        "cvss_v4_vector,cvss_v4_source,kev_date_added,kev_due_date,kev_name,jvndb_ids,jvn_title_ja,jvn_cvss_v3_score,"
        "jvn_cvss_v3_severity,jvn_last_updated,jvn_url,nvd_description_en").split(",")
key = lambda c: tuple(int(x) if x.isdigit() else 0 for x in c.split("-")[1:])
with open(a.out, "w", newline="", encoding="utf-8") as fo:
    w = csv.writer(fo, lineterminator="\n")
    w.writerow(COLS)
    for cve in sorted(set(nvd) | set(jvn), key=key):
        n, js = nvd.get(cve, {}), jvn.get(cve, [])
        cwe_jvn = uniq(c for _, j in js for c in j["cwe"])
        srcs = [("nvd", n.get("cwe_nvd", [])), ("cna_adp", n.get("cwe_other", [])), ("jvn", cwe_jvn)]
        if a.prefer == "jvn":
            srcs = [srcs[2], srcs[0], srcs[1]]
        sel, frm = next(((real(l), s) for s, l in srcs if real(l)), (None, None))
        if sel is None:                              # không nguồn nào có CWE thật: giữ mã giả nếu có
            sel, frm = next(((l[:1], "pseudo") for _, l in srcs if l), ([], "none"))
        conflict = "Y" if len({frozenset(real(l)) for _, l in srcs if real(l)}) > 1 else ""
        hits = [h for c in sel for h in kb.get(c, [])]
        ipa = sorted({i for i, _ in hits})
        status = "MAPPED" if ipa else ("OUT_OF_IPA_SCOPE" if real(sel) else "NO_CWE_INFO")
        best = max((mk for _, mk in hits), key=RANK.get, default="")
        any_ipa = sorted({i for _, l in srcs for c in real(l) for i, _ in kb.get(c, [])})
        j0 = js[0][1] if js else {}
        w.writerow([cve, f"https://nvd.nist.gov/vuln/detail/{cve}" if n else "", n.get("status", ""), n.get("published", ""),
                    n.get("modified", ""), n.get("cna", ""), "|".join(n.get("cwe_nvd", [])), "|".join(n.get("cwe_other", [])),
                    "|".join(n.get("other_src", [])), "|".join(cwe_jvn), "|".join(sel), frm, conflict, status, "|".join(ipa),
                    best, "|".join(any_ipa)] + (n.get("v3") or [""] * 4) + (n.get("v4") or [""] * 4) + (n.get("kev") or [""] * 3)
                   + ["|".join(jid for jid, _ in js), j0.get("title", ""), *(j0.get("cvss3") or ["", ""]), j0.get("updated", ""),
                      j0.get("url", ""), n.get("desc", "")])
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

def norm(v):
    """'CWE-89: ...' / '89' / 89 / 'CWE-79' -> 'CWE-89'; mã giả giữ nguyên nếu KB có; '-1', '0', '' -> None."""
    s = str(v).strip()
    if s in kbw:
        return s
    m = re.match(r"(?:CWE-)?(\d+)", s, re.I)
    return f"CWE-{int(m[1])}" if m and int(m[1]) > 0 else None

def by_cwe(cwes):
    """Tra danh sách CWE trong kb_cwe -> (ipa_status, ipa_ids)."""
    cwes = [c for c in dict.fromkeys(cwes) if c]
    if not cwes:
        return "NO_CWE_INFO", ""
    known = [c for c in cwes if c in kbw]
    if not known:
        return "UNKNOWN_CWE", ""                     # CWE không có trong KB (ví dụ bản CWE cũ hơn KB)
    ipa = sorted({r["ipa_id"] for c in known for r in kbw[c] if r["ipa_status"] == "MAPPED"})
    if ipa:
        return "MAPPED", "|".join(ipa)
    pseudo = all(kbw[c][0]["ipa_status"] == "NO_CWE_INFO" for c in known)
    return ("NO_CWE_INFO" if pseudo else "OUT_OF_IPA_SCOPE"), ""

COLS = ["tool", "check_id", "location", "lookup", "cwe_used", "cwe_from", "tool_cwe", "ipa_status", "ipa_ids",
        "cvss_v3", "kev_date_added", "jvndb_ids", "note"]
out = []
def emit(tool, check, loc, lookup, cwes, frm, tool_cwe, status, ipa, cve=None, note=""):
    out.append([tool, check, loc, lookup, "|".join(c for c in cwes if c), frm, "|".join(c for c in tool_cwe if c), status, ipa,
                (cve or {}).get("cvss_v3_score", ""), (cve or {}).get("kev_date_added", ""), (cve or {}).get("jvndb_ids", ""), note])

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
    elif tool == "trivy":                         # lỗ hổng gói: tra theo CVE trước (CWE của NVD/JVN), rồi mới tới CWE của Trivy
        for res in d.get("Results", []):
            for v in res.get("Vulnerabilities") or []:
                vid, loc = v["VulnerabilityID"], f'{res["Target"]} :: {v["PkgName"]}@{v.get("InstalledVersion", "")}'
                tcw = [norm(x) for x in v.get("CweIDs") or []]
                row = kbv.get(vid)
                if row:
                    kcw = [c for c in row["cwe_selected"].split("|") if c]
                    note = "CWE của Trivy khác KB" if set(filter(None, tcw)) and set(filter(None, tcw)) != set(kcw) else ""
                    emit(tool, vid, loc, "CVE", kcw, "kb:" + row["cwe_selected_from"], tcw, row["ipa_status"], row["ipa_ids"], row, note)
                else:
                    emit(tool, vid, loc, "CWE", tcw, "tool", tcw, *by_cwe(tcw), note="CVE không có trong KB")
            for m in res.get("Misconfigurations") or []:
                emit(tool, m["ID"], res["Target"], "-", [], "", [], "NO_CWE_INFO", "", note="misconfig: không có CWE/CVE")
            for s in res.get("Secrets") or []:
                emit(tool, s["RuleID"], res["Target"], "-", [], "", [], "NO_CWE_INFO", "", note="secret: không có CWE/CVE")

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
| JVN iPedia | Tải `checksum.txt`, so `sha256` từng feed (RSS theo năm, chi tiết theo năm) | Mỗi ngày | Tải lại feed đổi; sinh lại `kb_cwe.csv` (tên tiếng Nhật) và `kb_cve.csv` |
| CWE (MITRE) | Phiên bản catalog (tài liệu 02 mục 10) | Hằng tuần | Sinh lại `kb_cwe.csv`; kiểm tra CWE trong `ipa_cwe_map` còn tồn tại, không Deprecated |
| IPA (tài liệu hướng dẫn) | Băm nội dung trang/PDF (tài liệu 02 mục 10) | Hằng tuần | Người cập nhật `templates/ipa_*.csv`, rồi sinh lại `kb_cwe.csv` |

Nguyên tắc:

- **`kb_cwe.csv` commit vào git**: nhỏ, xác định từng byte. Mỗi PR cập nhật cho thấy đúng dòng nào đổi, người duyệt nhìn được mapping IPA thay đổi ra sao. Thay đổi từ IPA không tự merge.
- **`kb_cve.csv` không commit**: lớn và đổi mỗi ngày. Sinh trong CI hoặc job, nạp vào DB hoặc lưu thành artifact có kèm `source_version.csv`. Báo cáo scan ghi phiên bản KB đã dùng.
- **Kiểm tra trước khi phát hành** `kb_cve`: sha256 khớp `.meta`; không trùng `cve_id`; số CVE không giảm bất thường; tỉ lệ `MAPPED`/`NO_CWE_INFO` không lệch đột ngột so với lần trước; liệt kê CVE có `cwe_conflict = Y` mới phát sinh để người xem.
- **Không phụ thuộc host bị chặn**: nếu NVD hoặc JVN tạm không truy cập được, dùng bản KB gần nhất và đánh dấu `error` trong `source_version.csv`.
- **Cùng một CVE có ở nhiều file** (feed năm, feed Modified, trang API): `build_kb_cve.py` giữ bản có `lastModified` mới nhất, không phụ thuộc thứ tự file.
- **Các bước cụ thể và script đã chạy thử** (đồng bộ feed có kiểm tra sha256, client NVD API, kiểm tra trước khi phát hành, job hằng ngày): [tài liệu 05, tiếng Anh](05-kb-build-runbook.md).

---

## 8 · Giới hạn, việc cần người, bước tiếp

**Giới hạn của bản hiện tại**

- Mapping IPA↔CWE là **seed chưa xác minh**; mọi số liệu IPA ở trên phụ thuộc bản seed này.
- CWE 4.14 (2024-02-29) đã cũ; view 1003 và cây CWE có thể đã đổi ở bản mới.
- Dữ liệu JVN là fixture snapshot 2023-11-02, chỉ 13 bản ghi; tên tiếng Nhật mới có 8 CWE và 1 mã giả.
- Mã giả `CWE-Other` của JVN (nếu có) chưa thấy trong dữ liệu nên chưa có dòng trong `kb_cwe`; nếu công cụ gặp mã này sẽ ra `UNKNOWN_CWE`.
- Chưa chạy Trivy/ZAP thật (tài liệu 02 mục 11).
- Điều khoản sử dụng dữ liệu NVD, JVN iPedia và mirror chưa được đọc **[chưa xác minh]**.

**Việc cần người**

1. Mở host `services.nvd.nist.gov`, `jvndb.jvn.jp`, `www.ipa.go.jp` (hoặc dùng mirror và đồng ý điều khoản), để KB lấy dữ liệu trực tiếp thay vì qua mirror/fixture.
2. Người đọc tiếng Nhật đối chiếu bảng IPA↔CWE với tài liệu gốc của IPA và JVN iPedia, rồi nâng `mapping_status` lên `verified`.
3. Chọn chính sách CWE cho CVE: giữ mặc định NVD → CNA/ADP → JVN, hay ưu tiên JVN.
4. Quyết định có mở rộng mục IPA cho CWE-434, 98, 918, 502 (nhiều CVE nhưng ngoài 11 mục) hay không.

**Bước tiếp**

1. Tải toàn bộ feed JVN theo năm, sinh lại `kb_cwe.csv` với đủ tên tiếng Nhật.
2. Tải CWE mới nhất, sinh lại `kb_cwe.csv`, so view 1003 cũ/mới.
3. Dựng job hằng ngày sinh `kb_cve.csv` cho toàn bộ NVD, kèm các kiểm tra ở mục 7.
4. Chạy Semgrep/ZAP/Trivy thật trên một ứng dụng thử nghiệm, tra vào KB và xem lại các dòng `cwe_conflict`.

---

## 9 · Nguồn

Đã đọc trực tiếp / chạy thật trong phiên:

- Mirror NVD [`fkie-cad/nvd-json-data-feeds`](https://github.com/fkie-cad/nvd-json-data-feeds): README, 23 bản ghi CVE lẻ, release `CVE-Recent.json.xz` và `CVE-2025.json.xz` cùng file `.meta` (sha256 đã đối chiếu).
- [`vulsio/go-cve-dictionary`](https://github.com/vulsio/go-cve-dictionary) commit `d1af699` (2026-10-02): mã tải NVD/JVN, URL feed JVN.
- [`MaineK00n/vuls-data-update`](https://github.com/MaineK00n/vuls-data-update) commit `969aa0a` (2026-10-26): kiểu dữ liệu và fixture thật của feed RSS/chi tiết JVN iPedia, `checksum.txt`.
- Dữ liệu CWE 4.14 (gói PyPI `cwe2`): view 1000, view 1003.
- Các template IPA trong `templates/`.

Chỉ qua kết quả WebSearch:

- NVD CVE API 2.0 (tham số, giới hạn): <https://nvd.nist.gov/developers/vulnerabilities>, <https://nvd.nist.gov/developers/api-workflows>, [nvdlib](https://nvdlibdocs.readthedocs.io/en/latest/_modules/nvdlib/cve.html)
- MyJVN API: <https://jvndb.jvn.jp/en/apis/>, [go-myjvn](https://beta.pkg.go.dev/github.com/spiegel-im-spiegel/go-myjvn), [Hitachi HIRT](https://www.hitachi.com/ja-jp/hirt/publications/hirt-pub/hirt-pub14009/)
- Feed JVN iPedia: <https://jvndb.jvn.jp/en/feed>, <https://jvndb.jvn.jp/en/schema/jvnrss.html>
