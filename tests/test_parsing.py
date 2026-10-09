#!/usr/bin/env python3
"""Offline tests: no network, no API keys. Run: python -m unittest -v"""
import unittest

from kfs.geocode import split_address
from kfs.mfds import clean_date, normalize

RECALL_ROW = {
    "RTRVLPRVNS": "식품원료로 허용되지 않는 부위(껍질,쥬스,라텍스) 포함",
    "CRET_DTM": "2026-10-08 17:52:53.140739",
    "DISTBTMLMT": "(소비기한) 2031.8.13",
    "ADDR": "경기도 고양시 일산동구 문봉길 6-37 (문봉동) G동",
    "MNFDT": "(제조일자) 2026.8.14",
    "PRDTNM": "알로에 추출물 분말",
    "PRDLST_CD_NM": "기타가공품",
    "BSSHNM": "주식회사 성원에프아이",
    "RTRVLDSUSE_SEQ": "3000235627",
    "RTRVL_GRDCD_NM": "1등급",
}

INSPECTION_ROW = {
    "CRET_DTM": "2026.03.23",
    "DISTBTMLMT": "2028.02.26",
    "STDR_STND": "10.0미만 mg/kg",
    "ADDR": "서울특별시 동대문구",
    "MNFDT": "데이터없음",
    "TEST_ITMNM": "금속성이물",
    "INSTT_NM": "인천광역시 보건환경연구원",
    "PRDTNM": "노니분말",
    "TESTANALS_RSLT": "39.84 mg/kg",
    "BSSHNM": "주식회사 생생드림",
    "RTRVLDSUSE_SEQ": "3000223482",
}


class DateTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(clean_date("2026-10-08 17:52:53.1"), "2026-10-08")
        self.assertEqual(clean_date("2026.3.5"), "2026-03-05")
        self.assertEqual(clean_date("(소비기한) 2031.8.13"), "2031-08-13")
        self.assertEqual(clean_date("데이터없음"), "")
        self.assertEqual(clean_date(None), "")


class AddressTests(unittest.TestCase):
    def test_full(self):
        self.assertEqual(split_address(RECALL_ROW["ADDR"]),
                         ("경기도", "고양시"))

    def test_district_only(self):
        self.assertEqual(split_address("서울특별시 동대문구"),
                         ("서울특별시", "동대문구"))

    def test_short_province(self):
        self.assertEqual(split_address("경기 고양시 덕양구"),
                         ("경기도", "고양시"))

    def test_sejong(self):
        self.assertEqual(split_address("세종특별자치시 조치원읍"),
                         ("세종특별자치시", ""))

    def test_garbage(self):
        self.assertEqual(split_address(""), ("", ""))
        self.assertEqual(split_address("Unknown place"), ("", ""))


class NormalizeTests(unittest.TestCase):
    def test_recall(self):
        rec = normalize("I0490", RECALL_ROW)
        self.assertEqual(rec["id"], "I0490-3000235627")
        self.assertEqual(rec["source"], "recall")
        self.assertEqual(rec["grade"], "1등급")
        self.assertEqual(rec["expiry"], "2031-08-13")
        self.assertEqual(rec["mfg_date"], "2026-08-14")
        self.assertIn("허용되지 않는", rec["reason_ko"])

    def test_inspection(self):
        rec = normalize("I2620", INSPECTION_ROW)
        self.assertEqual(rec["source"], "inspection")
        self.assertEqual(rec["test_item_ko"], "금속성이물")
        self.assertEqual(rec["mfg_date"], "")
        self.assertIn("39.84 mg/kg", rec["reason_ko"])
        self.assertIn("기준 10.0미만", rec["reason_ko"])


if __name__ == "__main__":
    unittest.main()
