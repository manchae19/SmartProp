"""Trạng thái Matrix: phân biệt "chưa có tuyến" với "chưa đo được".

Bộ đọc Matrix trả ba trạng thái cho mỗi căn:
  OK            — đo được, có số phút
  NO_ROUTE      — nhà cung cấp không có tuyến cho căn này
  NOT_MEASURED  — lượt đo dừng trước khi tới căn này (hết ngân sách thời gian)

Hai trạng thái cuối phải được báo khác nhau, và không căn nào trong số đó được
tính là đạt giới hạn cứng hay bị gán một số phút.
"""
import unittest

import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest


def cell(pid, seconds, status=None):
    """Một ô Matrix. `seconds=None` nghĩa là không có số phút."""
    if status is None:
        status = "OK" if seconds is not None else "NO_ROUTE"
    return {"propertyId": pid,
            "status": status,
            "distanceMeters": None if seconds is None else seconds * 10.0,
            "durationSeconds": seconds}


class Base(unittest.TestCase):
    def service(self, cells, names="abcdef"):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[fixtures.prop(f"property:{name}", 2000000000, 90 - index)
                   for index, name in enumerate(names)])
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "Công ty", "latitude": 16.06, "longitude": 108.22,
             "approximate": False}]
        b.commute_matrix.return_value = {"provider": "GEOAPIFY", "mode": "drive",
                                         "cells": cells}
        return s, b

    def confirm(self, s, question):
        first = s.chat(ChatRequest(question=question, requireGeneration=False))
        sid = first.evidence["session"]["id"]
        s.chat(ChatRequest(question="Toàn Đà Nẵng", sessionId=sid, requireGeneration=False))
        s.chat(ChatRequest(question="Nhập địa điểm khác", sessionId=sid, requireGeneration=False))
        return sid, s.chat(ChatRequest(question="123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
                                       sessionId=sid, requireGeneration=False))


class MatrixStatusTests(Base):
    def test_a_both_states_are_reported_separately(self):
        """Có cả NOT_MEASURED và NO_ROUTE: mỗi trạng thái có thông báo riêng."""
        s, _ = self.service([
            cell("a", 120.0),
            cell("b", None, "NO_ROUTE"),
            cell("c", None, "NOT_MEASURED"),
            cell("d", None, "NOT_MEASURED"),
        ], names="abcd")
        _, reply = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 20 phút.")
        notes = " ".join(reply.dataLimitations)

        self.assertIn("1 tin chưa có tuyến", notes)
        self.assertIn("2 tin chưa đo được thời gian đi làm trong lượt này", notes)
        # Hai trạng thái không được gộp thành một câu.
        self.assertNotIn("3 tin chưa có tuyến", notes)
        self.assertNotIn("3 tin chưa đo được", notes)

    def test_b_soft_priority_may_show_an_unmeasured_listing_without_minutes(self):
        """Ưu tiên mềm: căn chưa đo có thể hiện sau căn đã đo, không kèm số phút."""
        s, _ = self.service([
            cell("a", 600.0),
            cell("b", None, "NOT_MEASURED"),
        ], names="ab")
        _, reply = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm khoảng 10 phút.")

        ids = [p["id"] for p in reply.recommendedProperties]
        self.assertIn("property:a", ids)
        self.assertIn("property:b", ids)
        # Căn đã đo đứng trước căn chưa đo.
        self.assertLess(ids.index("property:a"), ids.index("property:b"))

        unmeasured = next(p for p in reply.recommendedProperties if p["id"] == "property:b")
        self.assertIsNone(unmeasured.get("commute"),
                          "căn chưa đo không được gán số phút")

        notes = " ".join(reply.dataLimitations)
        self.assertIn("chưa đo được thời gian đi làm", notes)

    def test_c_all_unmeasured_never_satisfies_a_hard_limit(self):
        """Cả 6 căn chưa đo: không căn nào được tính là đạt giới hạn cứng."""
        s, _ = self.service([cell(name, None, "NOT_MEASURED") for name in "abcdef"])
        _, reply = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 20 phút.")

        self.assertEqual(reply.recommendedProperties, [],
                         "không căn nào đạt giới hạn cứng khi chưa đo được")
        notes = " ".join(reply.dataLimitations)
        self.assertIn("6 tin chưa đo được thời gian đi làm trong lượt này", notes)
        self.assertNotIn("chưa có tuyến", notes)
        # Không được kết luận là không có nhà phù hợp.
        self.assertNotIn("không có nhà", notes.lower())

    def test_d_only_no_route_keeps_the_current_wording(self):
        """Chỉ có NO_ROUTE: giữ nguyên hành vi và câu chữ hiện tại."""
        s, _ = self.service([cell(name, None, "NO_ROUTE") for name in "abc"], names="abc")
        _, reply = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 20 phút.")

        self.assertEqual(reply.recommendedProperties, [])
        notes = " ".join(reply.dataLimitations)
        self.assertIn("chưa có tuyến", notes)
        self.assertNotIn("chưa đo được", notes)


if __name__ == "__main__":
    unittest.main()
