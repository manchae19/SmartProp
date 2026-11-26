"""WP-01 regression: canonical street matching + category cleaning.

Kiểm hàm thuần; không cần model artifact.
"""
import sys
import unicodedata

sys.path.insert(0, r"F:\SmartProp\.worktrees\v13-hardening-integration\ai-services")

from app.models.xgboost.features_v1_3 import canonical_street, clean_category  # noqa: E402

VOCAB = {"nguyễn văn linh", "nguyễn phước lan", "29/3", "đường láng", "trần phú", "trần phú 2"}


class TestCleanCategory:
    def test_casefold_and_nfc(self):
        assert clean_category("Nguyễn Văn Linh") == "nguyễn văn linh"

    def test_missing(self):
        assert clean_category(None) == "__MISSING__"
        assert clean_category("") == "__MISSING__"
        assert clean_category("   ") == "__MISSING__"


class TestCanonicalStreet:
    def test_exact_entry_is_kept(self):
        assert canonical_street("Nguyễn Văn Linh", VOCAB) == "nguyễn văn linh"

    def test_lowercase_matches(self):
        assert canonical_street("nguyễn văn linh", VOCAB) == "nguyễn văn linh"

    def test_prefix_stripped_when_it_reveals_a_known_street(self):
        assert canonical_street("Đường Nguyễn Văn Linh", VOCAB) == "nguyễn văn linh"
        assert canonical_street("đường nguyễn văn linh", VOCAB) == "nguyễn văn linh"
        assert canonical_street("Phố Nguyễn Phước Lan", VOCAB) == "nguyễn phước lan"

    def test_street_that_really_starts_with_prefix_word_stays_intact(self):
        # "đường láng" chính là một entry; cắt tiền tố sẽ làm hỏng nó.
        assert canonical_street("Đường Láng", VOCAB) == "đường láng"

    def test_whitespace_trimmed(self):
        assert canonical_street("  Nguyễn Văn Linh  ", VOCAB) == "nguyễn văn linh"

    def test_unknown_street_not_rewritten(self):
        out = canonical_street("Đường Không Tồn Tại XYZ 123", VOCAB)
        assert out not in VOCAB
        assert out == "đường không tồn tại xyz 123"

    def test_prefix_strip_never_invents_match(self):
        assert canonical_street("Đường Không Tồn Tại", VOCAB) not in VOCAB

    def test_empty_becomes_missing(self):
        assert canonical_street("", VOCAB) == "__MISSING__"
        assert canonical_street(None, VOCAB) == "__MISSING__"
        assert canonical_street("   ", VOCAB) == "__MISSING__"

    def test_no_collision_between_streets(self):
        a = canonical_street("Đường Trần Phú", VOCAB)
        b = canonical_street("Đường Trần Phú 2", VOCAB)
        assert a == "trần phú"
        assert b == "trần phú 2"
        assert a != b

    def test_unicode_forms_equivalent(self):
        composed = "Nguyễn Văn Linh"
        decomposed = unicodedata.normalize("NFD", composed)
        assert canonical_street(composed, VOCAB) == canonical_street(decomposed, VOCAB)

    def test_numeric_street_names_survive(self):
        assert canonical_street("29/3", VOCAB) == "29/3"
        assert canonical_street("Đường 29/3", VOCAB) == "29/3"
