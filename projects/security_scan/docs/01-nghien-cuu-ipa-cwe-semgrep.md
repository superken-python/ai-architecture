# 01 · Nghiên cứu IPA (Nhật Bản), CWE (MITRE) và Semgrep

Ngày nghiên cứu: 2026-10-27 · Tài liệu kế tiếp: [02 · Mapping Semgrep ↔ IPA và cập nhật liên tục](02-mapping-semgrep-ipa-va-cap-nhat.md)

## 0 · Đọc phần này trước: cái gì đã kiểm chứng, cái gì chưa

Phiên nghiên cứu chạy trong môi trường cloud có **chính sách mạng chặn một số host**. Hệ quả:

| Nguồn bạn yêu cầu | Kết quả | Cách mình bổ sung |
|---|---|---|
| `https://www.ipa.go.jp/` và 2 trang IPA (websecurity, CWE tiếng Anh) | **Bị chặn** (403 từ proxy), không đọc được nội dung | WebSearch (chỉ lấy được đoạn trích), kiến thức nền |
| `https://cwe.mitre.org/about/new_to_cwe.html` | **Bị chặn** | Gói PyPI `cwe2` đi kèm **dữ liệu CWE 4.14** (parse trực tiếp) + kiến thức nền |
| `https://semgrep.dev/` | **Bị chặn** | Cài `semgrep` 1.182.1 từ PyPI, clone repo `semgrep/semgrep-rules`, **chạy scan thật** |

Mỗi khẳng định dưới đây mang một nhãn nguồn:

- **[đã kiểm chứng]** — mình tự chạy/đọc dữ liệu trong phiên này (code, dữ liệu, số liệu có thể tái hiện theo tài liệu 02).
- **[tìm kiếm web]** — lấy từ đoạn trích kết quả WebSearch, nguồn thứ cấp, chưa đọc trang gốc.
- **[chưa xác minh]** — kiến thức nền của mình, **chưa đối chiếu được với trang gốc**. Cần người có quyền truy cập IPA kiểm tra lại trước khi dùng cho báo cáo chính thức.

> Để đọc trực tiếp 4 URL trên, thêm các host sau vào *Allowed domains* của environment (xem [hướng dẫn](https://code.claude.com/docs/en/cloud-environments#network-access)):
> `www.ipa.go.jp`, `cwe.mitre.org`, `cwe-api.mitre.org`, `semgrep.dev`, `jvndb.jvn.jp`. Hoặc gửi PDF/HTML đã tải về.

---

## 1 · IPA — 独立行政法人情報処理推進機構

**[chưa xác minh]** IPA (Information-technology Promotion Agency, Japan) là cơ quan độc lập của Nhật Bản về an toàn thông tin và nhân lực CNTT. Phần liên quan đến việc quét mã nguồn là mảng **hướng dẫn lập trình an toàn cho web** và **cơ sở dữ liệu lỗ hổng**.

### 1.1 Tài liệu IPA cần quan tâm

| Tài liệu / dịch vụ | Dùng để làm gì trong dự án này | URL | Nhãn |
|---|---|---|---|
| 安全なウェブサイトの作り方 (Cách xây dựng website an toàn) | **Nguồn chính của "IPA knowledge base"**: 11 loại lỗ hổng web, mỗi loại có đối sách *gốc rễ* và *bảo hiểm* | <https://www.ipa.go.jp/security/vuln/websecurity/about.html> (URL bạn cung cấp) | URL do bạn cung cấp; nội dung **[chưa xác minh]** |
| 共通脆弱性タイプ一覧 CWE 概説 (bản tiếng Nhật) | Giải thích CWE, cách IPA dùng CWE | <https://www.ipa.go.jp/security/vuln/CWE.html> | **[tìm kiếm web]** |
| CWE overview (bản tiếng Anh) | Như trên | <https://www.ipa.go.jp/en/security/vulnerabilities/cwe.html> | **[tìm kiếm web]** |
| Trang CWE trong mục SCAP | Xuất hiện trong kết quả tìm kiếm, chưa rõ nội dung | <https://www.ipa.go.jp/security/vuln/scap/cwe.html> | **[tìm kiếm web]**, chưa rõ nội dung |
| JVN iPedia / MyJVN API | CSDL lỗ hổng của Nhật, mỗi mục gắn loại CWE; có báo cáo thống kê theo quý | <https://jvndb.jvn.jp/> | **[tìm kiếm web]** (báo cáo quý) + **[chưa xác minh]** (API) |
| 安全なSQLの呼び出し方, ウェブ健康診断仕様, セキュア・プログラミング講座 | Tài liệu chi tiết hơn cho từng lỗi; có thể bổ sung mục ngoài 11 loại | tìm trên trang IPA | **[chưa xác minh]** (tên và nội dung) |

### 1.2 Những gì tìm kiếm web xác nhận về CWE tại IPA

Nguồn: trích đoạn kết quả WebSearch từ trang CWE tiếng Nhật/Anh và các báo cáo JVN iPedia theo quý của IPA **[tìm kiếm web]**.

- Trang tiếng Nhật ghi cập nhật **2025-07-03**; trang tiếng Anh ghi **2022-04-05** → **bản tiếng Anh của IPA có thể tụt hậu so với bản tiếng Nhật**.
- Trang nêu số mục CWE: 22 View, 105 Category, 638 Weakness, 12 Compound Element. So với CWE 4.14 mình parse được (963 Weakness, 409 Category, 54 View, xem mục 2.1) thì đây là **số liệu cũ** → IPA mô tả cấu trúc CWE ở một thời điểm, không phải catalog mới nhất.
- IPA tuyên bố "CWE-Compatible" từ 2008-10-03; MyJVN hỗ trợ CWE từ 2008-10-23.
- JVN iPedia (hết quý 2/2023): 158.560 lỗ hổng bản tiếng Nhật, 2.629 bản tiếng Anh. Quý 2/2023 phổ biến nhất là CWE-79 (460 ca) rồi CWE-89 (262 ca).
- Một tài liệu mua sắm của thành phố Yokohama (bên thứ ba, **không phải mapping chính thức của IPA**) có gắn CWE-601 cho open redirect và CWE-434 cho upload file dẫn tới thực thi script phía server.
- Tìm kiếm **không** tìm ra bảng chính thức nối 11 loại trong "安全なウェブサイトの作り方" với mã CWE.

**Ý nghĩa:** chưa có bằng chứng IPA công bố bảng IPA↔CWE ở dạng dữ liệu máy đọc được. Phải coi đây là việc **tự biên soạn rồi kiểm duyệt**, xem tài liệu 02.

### 1.3 Mười một loại lỗ hổng (bản seed, **[chưa xác minh]**)

Tên và thứ tự ghi theo trí nhớ về "改訂第7版". Cột CWE là **ứng viên** do mình chọn, **không phải** bảng chính thức của IPA. Đã nạp vào [`templates/ipa_item.csv`](../templates/ipa_item.csv) và [`templates/ipa_cwe_map.csv`](../templates/ipa_cwe_map.csv) với `verification_status = seed_unverified`.

| # | Tiếng Nhật | Tiếng Anh | CWE ứng viên |
|---|---|---|---|
| 1.1 | SQLインジェクション | SQL Injection | 89 |
| 1.2 | OSコマンド・インジェクション | OS Command Injection | 78 |
| 1.3 | パス名パラメータの未チェック／ディレクトリ・トラバーサル | Path Traversal | 22 |
| 1.4 | セッション管理の不備 | Session Management Flaws | 384, 613 (+614, 1004 liên quan yếu) |
| 1.5 | クロスサイト・スクリプティング | XSS | 79 |
| 1.6 | CSRF | CSRF | 352 |
| 1.7 | HTTPヘッダ・インジェクション | HTTP Header Injection | 113 |
| 1.8 | メールヘッダ・インジェクション | Mail Header Injection | 93 *(chưa chắc IPA dùng mã nào)* |
| 1.9 | クリックジャッキング | Clickjacking | 1021 |
| 1.10 | バッファオーバーフロー | Buffer Overflow | 119 (CWE-120/787/125 là con) |
| 1.11 | アクセス制御や認可制御の欠落 | Missing Access/Authorization Control | 285 (862, 863 là con) |

### 1.4 Cấu trúc đối sách của IPA (**[chưa xác minh]**)

Mỗi loại lỗ hổng có hai nhóm đối sách: **根本的解決** (giải quyết tận gốc, ví dụ dùng placeholder cho SQL) và **保険的対策** (lớp phòng thủ bổ sung, ví dụ không hiện thông báo lỗi thô). Đây là phần giá trị nhất để gắn vào kết quả scan: mỗi finding đã map được sang IPA thì kèm luôn hướng sửa. Schema: [`templates/ipa_countermeasure.csv`](../templates/ipa_countermeasure.csv).

---

## 2 · CWE — Common Weakness Enumeration (MITRE)

### 2.1 Cấu trúc **[đã kiểm chứng trên CWE 4.14, phát hành 2024-02-29]**

| Thực thể | Số lượng trong 4.14 | Ghi chú |
|---|---|---|
| Weakness | 963 | Mục chính; có `Abstraction` = Pillar / Class / Base / Variant / Compound |
| Category | 409 | Nhóm theo chủ đề, **không phải** lỗi cụ thể; nhiều mục `Obsolete` |
| View | 54 | Cách nhìn: view **1000** (Research Concepts, cây cha–con đầy đủ), 699 (Software Development), 1003 (tập con cho CVE/NVD), các view Top 25, OWASP... |

- Quan hệ cha–con nằm trong `Related_Weakness` với `Nature="ChildOf"` và `View_ID="1000"`. Ví dụ: CWE-89 `ChildOf` CWE-943; CWE-78 `ChildOf` CWE-77; CWE-113 `ChildOf` CWE-93 và CWE-436.
- Trạng thái (`Status`): Stable / Draft / Incomplete / Deprecated / Obsolete. Cả 164 CWE mà Semgrep dùng đều tồn tại trong 4.14, nhưng 5 mục trong đó là Category chứ không phải Weakness, và **CWE-320 là Category đã Obsolete** mà Semgrep vẫn dùng làm tag cho 51 rule.

CWE ứng viên của 11 mục IPA, tra trong CWE 4.14 **[đã kiểm chứng sự tồn tại; mapping sang IPA vẫn chưa xác minh]**:

| CWE | Tên | Abstraction | Status |
|---|---|---|---|
| 89 | SQL Injection | Base | Stable |
| 78 | OS Command Injection | Base | Stable |
| 22 | Path Traversal | Base | Stable |
| 384 | Session Fixation | Compound | Incomplete |
| 613 | Insufficient Session Expiration | Base | Incomplete |
| 79 | Cross-site Scripting | Base | Stable |
| 352 | CSRF | Compound | Stable |
| 113 | HTTP Request/Response Splitting | Variant | Incomplete |
| 93 | CRLF Injection | Base | Draft |
| 1021 | Improper Restriction of Rendered UI Layers or Frames | Base | Incomplete |
| 119 | Improper Restriction of Operations within the Bounds of a Memory Buffer | Class | Stable |
| 285 | Improper Authorization | Class | Draft |
| 862 / 863 | Missing / Incorrect Authorization | Class | Incomplete |

### 2.2 Định dạng tải về

- Trang tải: <https://cwe.mitre.org/data/downloads.html> **[đã kiểm chứng]** (ghi trong file `cwe.ABOUT` của gói `cwe2`).
- XML toàn catalog (`cwec_vX.Y.xml`, schema `cwe-7`) và CSV theo từng view **[đã kiểm chứng định dạng]** — đã parse file XML 4.14 và đọc CSV đi kèm.
- CSV theo view có các cột: `CWE-ID, Name, Weakness Abstraction, Status, Description, Extended Description, Related Weaknesses, ..., Taxonomy Mappings, Related Attack Patterns, Notes`. Cột `CWE-ID` là số trần (không có tiền tố `CWE-`). Cột `Related Weaknesses` mã hóa theo dạng `::NATURE:ChildOf:CWE ID:489:VIEW ID:1000:ORDINAL:Primary::`, cần tách chuỗi.
- Tên các URL `cwec_latest.xml.zip` và REST API `https://cwe-api.mitre.org/api/v1/cwe/version` **[chưa xác minh]** — mình chưa gọi được. Kiểm tra lại khi có mạng (ghi sẵn trong [`source_version.csv`](../templates/source_version.csv)).
- **Bản `cwe2` bundle là 4.14 (2024-02-29)**, không phải bản mới nhất. Chỉ dùng để dựng và kiểm thử pipeline; bản dùng thật phải tải trực tiếp từ MITRE.
- Giấy phép: gói `cwe2` kèm file `cwe-tou` (điều khoản sử dụng CWE). Đọc kỹ trước khi phân phối lại dữ liệu CWE.

---

## 3 · Semgrep

### 3.1 Là gì, chạy thế nào

**[chưa xác minh]** Semgrep là công cụ SAST khớp mẫu trên cây cú pháp, có chế độ *taint* (theo dõi dữ liệu từ nguồn vào nơi nguy hiểm). Bản Community Edition (CE) là mã nguồn mở.

**[đã kiểm chứng]** Chạy ngoại tuyến hoàn toàn bằng rule cục bộ:

```bash
pip install semgrep                      # đã thử: 1.182.1
git clone --depth 1 https://github.com/semgrep/semgrep-rules.git
semgrep scan --metrics=off --disable-version-check \
  --config semgrep-rules/python --json -o scan.json  src/
# SARIF thay cho JSON:  --sarif -o scan.sarif
```

Rule lấy từ registry `semgrep.dev` (ví dụ `--config p/owasp-top-ten`) **không dùng được** trong môi trường này vì host bị chặn; repo `semgrep-rules` là kho nguồn của các rule đó.

**Giấy phép rule [đã kiểm chứng]:** file `LICENSE` của `semgrep-rules` là *Semgrep Rules License v1.0* (<https://semgrep.dev/legal/rules-license>). Đọc điều khoản trước khi nhúng rule vào sản phẩm/dịch vụ hoặc phân phối lại; dùng nội bộ để scan là việc khác với phân phối lại.

### 3.2 Metadata của rule

Trích từ rule thật `python/lang/security/deserialization/avoid-pyyaml-load.yaml` **[đã kiểm chứng]**:

```yaml
rules:
- id: avoid-pyyaml-load
  metadata:
    owasp: ['A08:2017 - Insecure Deserialization', 'A08:2021 - Software and Data Integrity Failures', 'A08:2025 - Software or Data Integrity Failures']
    cwe: ['CWE-502: Deserialization of Untrusted Data']
    category: security
    technology: [pyyaml]
    subcategory: [audit]
    likelihood: LOW
    impact: MEDIUM
    confidence: MEDIUM
  languages: [python]
  severity: ERROR
```

Schema metadata (`metadata-schema.yaml.schm` trong repo) **[đã kiểm chứng]**: `category` ∈ security / correctness / best-practice / ...; `cwe` là chuỗi **hoặc** list, khớp `^CWE-\d+.*`; `confidence`, `likelihood`, `impact` ∈ LOW/MEDIUM/HIGH; `subcategory` ∈ audit / vuln / secure default; có thêm `owasp`, `references`, `technology`, `asvs`, `source-rule-url`.

### 3.3 Output khi scan

**JSON** — đường dẫn quan trọng cho mapping **[đã kiểm chứng trên Semgrep 1.182.1]**:

```json
{
  "check_id": "rules-src.semgrep-rules.python.flask.security.audit.debug-enabled",
  "path": "target/vuln_app.py",
  "start": {"line": 58, "col": 5}, "end": {"line": 58, "col": 40},
  "extra": {
    "message": "Detected Flask app with debug=True. ...",
    "severity": "WARNING",
    "metadata": {
      "cwe": ["CWE-489: Active Debug Code"],
      "owasp": "A06:2017 - Security Misconfiguration",
      "confidence": "HIGH", "likelihood": "HIGH", "impact": "MEDIUM",
      "category": "security", "subcategory": ["vuln"], "technology": ["flask"]
    },
    "lines": "requires login",
    "fingerprint": "requires login"
  }
}
```

**SARIF** đặt CWE và OWASP vào `runs[].tool.driver.rules[].properties.tags` dưới dạng chuỗi `"CWE-489: Active Debug Code"`, `"OWASP-A06:2017 - Security Misconfiguration"`; `results[].locations[].physicalLocation.region.snippet.text` **có** đoạn mã.

### 3.4 Bẫy khi lấy CWE từ output Semgrep (tất cả **[đã kiểm chứng]**)

1. **`cwe` lúc là list, lúc là chuỗi** (khoảng 10% rule dùng chuỗi); `owasp` cũng vậy. Luôn chuẩn hóa về list.
2. **`cwe` là chuỗi có cả tên** (`"CWE-89: Improper Neutralization..."`), phải tách lấy số bằng regex.
3. **`check_id` có tiền tố đường dẫn của `--config`** (`rules-src.semgrep-rules.python...`) và **không chứa tên file** trong chế độ thư mục. Phải khớp theo hậu tố `<thư mục chấm>.<rule id>`.
4. **`rule id` không duy nhất**: 64 id xuất hiện ở nhiều file (`tainted-sql-string` có 13 biến thể theo ngôn ngữ/framework), và 2 hậu tố đầy đủ vẫn trùng. Khóa thật là `(rule_file, rule_id)`.
5. **`lines` và `fingerprint` chỉ là chuỗi `"requires login"`** trong bản OSS. Muốn có đoạn mã thì đọc lại file nguồn theo `start`/`end`, hoặc dùng SARIF.
6. **Tag CWE có thể sai.** Trong 13 biến thể `tainted-sql-string`, 11 gắn CWE-89 (SQL Injection) nhưng bản Django gắn CWE-915 và bản Flask gắn CWE-704. Rule `avoid_hardcoded_config_SECRET_KEY` gắn CWE-489 (Active Debug Code) dù bản chất là hard-code bí mật (CWE-798). Rule `ruby/lang/security/filter-skipping` (route Rails có thể render view tùy ý) gắn CWE-1021 (clickjacking) và là rule duy nhất trong repo mang CWE này. Cần **lớp override có người duyệt**.
7. **Một số CWE là Category/Obsolete**, không phải Weakness: 310, 16, 264, 399, 320 (CWE 4.14).
8. **Metadata không đồng nhất**: 201/1.649 rule (12,2%) không có `owasp`; một rule có thể liệt kê đồng thời nhãn OWASP 2017, 2021 và 2025; 11 rule có `severity: MEDIUM` (ngoài tập INFO/WARNING/ERROR).
9. **Không có finding ≠ an toàn.** Trên file mẫu có 3 lỗi cố ý mà `semgrep-rules/python` không báo: `yaml.load(cfg)` (rule `avoid-pyyaml-load` chủ ý chỉ bắt `yaml.Loader`/`unsafe_load`, không phải lỗi rule), hard-code `DB_PASSWORD` và path traversal qua `send_file(os.path.join(...))` (không có rule khớp trong thư mục `python/`). Chưa thử ruleset nào khác của registry.

### 3.5 Số liệu bộ rule `semgrep-rules` **[đã kiểm chứng]**

Commit `16b9e6d45f10649f6a531ec4838ed9924372c3bc` (2026-10-21), bỏ thư mục `problem-based-packs` (rule trùng) và file `*.test.yaml`:

| Chỉ số | Giá trị |
|---|---|
| Tổng rule | 2.091 |
| Rule `category: security` | 1.649 (**100% đều có tag `cwe`**) |
| Cặp rule–CWE | 1.662 (10 rule gắn nhiều hơn 1 CWE) |
| CWE khác nhau | 164 |
| Rule thiếu `owasp` | 201 (12,2%) |

CWE xuất hiện nhiều nhất (theo số cặp rule–CWE):

| CWE | Số rule | Tên | Thuộc 11 mục IPA? |
|---|---|---|---|
| 798 | 265 | Use of Hard-coded Credentials | Không |
| 79 | 129 | Cross-site Scripting | **Có** (1.5) |
| 1220 | 108 | Insufficient Granularity of Access Control | Không theo bản seed (cùng cha CWE-284 với CWE-285 của mục 1.11 nhưng không phải con của nó; ứng viên để người duyệt cân nhắc) |
| 89 | 79 | SQL Injection | **Có** (1.1) |
| 78 | 65 | OS Command Injection | **Có** (1.2) |
| 327 | 58 | Broken or Risky Cryptographic Algorithm | Không |
| 320 | 51 | Key Management Errors (Category, Obsolete) | Không |
| 94 | 49 | Code Injection | Không |
| 326 | 49 | Inadequate Encryption Strength | Không |
| 918 | 42 | SSRF | Không |
| 502 | 42 | Deserialization of Untrusted Data | Không |
| 319 | 39 | Cleartext Transmission of Sensitive Information | Không |

### 3.6 Lần scan mẫu **[đã kiểm chứng]**

Một file Flask giả (`vuln_app.py`, ~60 dòng, có SQLi, OS command, XSS, open redirect, MD5, `verify=False`, `debug=True`...) quét bằng `semgrep-rules/python` (371 rule) cho **20 finding**. Chi tiết gộp theo IPA ở [tài liệu 02, mục 6](02-mapping-semgrep-ipa-va-cap-nhat.md#6--ví-dụ-end-to-end-chạy-thật).

---

## 4 · Kết luận nghiên cứu

1. Cầu nối kỹ thuật tự nhiên là **CWE**: Semgrep gắn CWE vào rule; IPA dùng CWE làm ngôn ngữ chung (JVN iPedia, CWE-Compatible). Chuỗi mapping là `finding → rule → CWE → mục IPA → đối sách IPA`.
2. **11 mục của "安全なウェブサイトの作り方" chỉ phủ khoảng một phần tư** những gì Semgrep tag (đo ở tài liệu 02). Hard-code credential, mật mã, SSRF, deserialization, XXE... không có mục tương ứng → mapping phải có trạng thái "ngoài phạm vi IPA" và nên mở rộng sang tài liệu IPA khác.
3. **Không có nguồn xuất sẵn (export) cho bảng IPA↔CWE** mà mình xác nhận được. Phải biên soạn một lần, có người kiểm duyệt đối chiếu bản PDF, rồi quản lý như dữ liệu có phiên bản.
4. Trước khi dùng cho báo cáo chính thức: mở trang IPA, đối chiếu tên 11 mục, số thứ tự, mã CWE IPA thật sự dùng, và nguyên văn đối sách (cột `text_ja`).
5. Tài liệu này chỉ nói về Semgrep. **Trivy và ZAP** (cũng mã nguồn mở; ZAP gắn `cweid` cho mỗi alert, Trivy chỉ gắn `CweIDs` cho lỗ hổng thư viện) được nghiên cứu ở [tài liệu 02, mục 2](02-mapping-semgrep-ipa-va-cap-nhat.md#2--trivy-và-zap-mã-nguồn-mở-không-output-có-cwe-không).
6. Knowledge base **IPA + NVD** mà cả ba công cụ tra vào (template CSV, export, cập nhật liên tục) ở [tài liệu 03](03-kb-ipa-nvd-cho-cong-cu.md).
