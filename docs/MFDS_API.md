# The MFDS open API, as actually observed

Everything here was checked with `curl` on 2026-10-09 before any
client code was written. If something stops matching, re-probe
before you patch.

## One URL shape for every service

```
https://openapi.foodsafetykorea.go.kr/api/{key}/{service}/{xml|json}/{start}/{end}
https://openapi.foodsafetykorea.go.kr/api/{key}/{service}/json/{start}/{end}/{FIELD=value}
```

- Plain GET. No headers, no OAuth. The key rides in the path.
- `start` and `end` are 1-based row positions, inclusive.
  At most 1000 rows per call (`ERROR-336` above that).
- The optional trailing segment filters on a whitelisted field. Each
  service whitelists its own. For I0490 only `CHNG_DT`, `CRET_DTM`,
  `PRDLST_REPORT_NO` are accepted; an unknown field is ignored and the
  `RESULT.MSG` tells you so.

Try it yourself:

```bash
curl -s "https://openapi.foodsafetykorea.go.kr/api/sample/I0490/json/1/5" | python3 -m json.tool
```

## Response envelope

```json
{
  "I0490": {
    "total_count": "383",
    "row": [ { ...one record... }, ... ],
    "RESULT": { "MSG": "정상처리되었습니다.", "CODE": "INFO-000" }
  }
}
```

The root key is the service id. `total_count` is a string. On an
error there is no service wrapper, only a top-level `RESULT`.

| CODE | Meaning |
|---|---|
| INFO-000 | OK |
| INFO-200 | No rows for this query |
| INFO-100 | Key not registered |
| INFO-300 | Key invalid |
| ERROR-300 | Required value missing |
| ERROR-301 | File type must be xml or json |
| ERROR-336 | More than 1000 rows requested |
| ERROR-500/600/601 | Server, DB, SQL error |

## The `sample` key

The literal key `sample` works without an account. It returns the
same five rows for any `start`/`end`, ignores filters, and does not
page. Good for learning the schema, useless for analysis. `kfs`
detects it and stops after one page.

## Getting a personal key (free)

1. https://www.foodsafetykorea.go.kr/api/ (식품안전나라 공공데이터활용)
2. Log in. Registration needs a Korean mobile number or i-PIN, so a
   Korean colleague is the quickest route.
3. 인증키 신청 for each service you want (one application per
   service, one time). Daily call limits per service: I0490 2000,
   I2620 500.
4. `export MFDS_API_KEY=...` or put it in `.env`.

The equivalent datasets also exist on data.go.kr with a different
auth style (`serviceKey` query parameter). Do not mix the two.

## Services used

### I0490 회수·판매중지 정보 (recalls and sales suspensions)

| Field | Korean | Meaning |
|---|---|---|
| RTRVLDSUSE_SEQ | 회수일련번호 | Recall serial (unique) |
| PRDTNM | 제품명 | Product name |
| BSSHNM | 업소명 | Business name |
| ADDR | 주소 | Business address |
| RTRVLPRVNS | 회수사유 | Reason for recall |
| RTRVL_GRDCD_NM | 회수등급 | Recall grade 1등급 (most serious) to 3등급 |
| RTRVLPLANDOC_RTRVLMTHD | 회수방법 | Recall method |
| PRDLST_CD_NM | 식품유형 | Food type |
| PRDLST_TYPE | 제품유형 | Product type (가공식품 etc.) |
| PRDLST_REPORT_NO | 품목제조보고번호 | Product report number |
| LCNS_NO | 인허가번호 | Business licence number |
| MNFDT | 제조일자 | Manufacture date, free text |
| DISTBTMLMT | 소비기한 | Use-by date, free text |
| FRMLCUNIT | 포장단위 | Package unit |
| BRCDNO | 바코드 | Barcode |
| IMG_FILE_PATH | 이미지 | Product image URL |
| TELNO | 전화번호 | Phone |
| CRET_DTM | 등록일시 | Registered timestamp |
| PRDLST_CD | 식품유형코드 | Food type code |

### I2620 검사부적합(국내) (domestic inspection non-conformities)

| Field | Korean | Meaning |
|---|---|---|
| RTRVLDSUSE_SEQ | 일련번호 | Serial |
| PRDTNM | 제품명 | Product name |
| BSSHNM | 업소명 | Business name |
| ADDR | 주소 | Business address (often district only) |
| TEST_ITMNM | 검사항목 | Test item (e.g. 금속성이물, 대장균) |
| TESTANALS_RSLT | 검사결과 | Measured result |
| STDR_STND | 기준규격 | The standard it failed |
| INSTT_NM | 검사기관 | Testing agency |
| PRDLST_CD_NM | 식품유형 | Food type |
| PRDLST_REPORT_NO | 품목제조보고번호 | Product report number |
| LCNS_NO | 인허가번호 | Licence number |
| MNFDT | 제조일자 | Manufacture date (may be 데이터없음) |
| DISTBTMLMT | 소비기한 | Use-by date |
| FRMLCUNIT | 포장단위 | Package unit |
| BRCDNO | 바코드 | Barcode |
| REGSTR_TELNO, REPORTR_TELNO | 전화번호 | Phones |
| CRET_DTM | 등록일 | Registered date |

Date fields are free text in several formats. `kfs.mfds.clean_date`
normalises them and is covered by tests.

## Other services worth a look (all probed, all work with `sample`)

| Service | What | Rows |
|---|---|---|
| I2630 | 행정처분 (administrative dispositions, with address and violation text) | 2725 |
| I2810 | 수입식품 부적합 공고 (imported food non-conformity notices) | 532 |
| I0030 / C003 | 건강기능식품 품목 (health functional food products) | 45874 |
| C005 | 바코드연계제품정보 (barcode-linked products) | large |
| I2790 | 식품영양성분DB (nutrition database) | large |

Adding I2630 to this app is a natural first exercise: it has the same
address field, so the map and geocoder work unchanged.
