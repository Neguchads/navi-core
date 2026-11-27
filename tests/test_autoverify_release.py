import copy
import unittest

from navi_core.autoverify_release import select_asset, MAX_BYTES

TAG = "v1.3.0"
NAME = "game.exe"
SHA = "a" * 64
REPO = "Neguchads/cdos-nintendods-recomp"


def fixture():
    return {"tag_name": TAG, "draft": False, "prerelease": False, "assets": [
        {"id": 42, "name": NAME, "size": 1234, "state": "uploaded",
         "digest": "sha256:" + SHA}]}


class AutoVerifyReleaseTests(unittest.TestCase):
    def test_matching_asset(self):
        result = select_asset(fixture(), TAG, NAME, SHA, REPO)
        self.assertEqual(result["asset_id"], 42)
        self.assertEqual(result["sha256"], SHA)

    def test_bad_input(self):
        for tag, name, sha in [("../x", NAME, SHA), (TAG, "../game.exe", SHA),
                               (TAG, "game.nds", SHA), (TAG, "*.exe", SHA),
                               (TAG, NAME, "bad")]:
            with self.subTest(tag=tag, name=name, sha=sha):
                with self.assertRaises(ValueError):
                    select_asset(fixture(), tag, name, sha, REPO)

    def test_reject_nonfinal_and_unlisted(self):
        with self.assertRaises(ValueError):
            select_asset(fixture(), TAG, NAME, SHA, "Neguchads/navi-core")
        with self.assertRaises(ValueError):
            select_asset(fixture(), TAG + "-rc.1", NAME, SHA, REPO)

    def test_bad_metadata(self):
        for field, value in [("digest", None), ("digest", "sha256:" + "b" * 64),
                             ("size", 0), ("size", MAX_BYTES + 1), ("size", True),
                             ("state", "new"), ("id", False)]:
            with self.subTest(field=field, value=value):
                data = fixture()
                data["assets"][0][field] = value
                with self.assertRaises(ValueError):
                    select_asset(data, TAG, NAME, SHA, REPO)

    def test_draft_wrong_tag_and_ambiguity(self):
        for field, value in [("draft", True), ("prerelease", True), ("tag_name", "v0.0.1"),
                             ("assets", []), ("assets", fixture()["assets"] * 2)]:
            with self.subTest(field=field):
                data = copy.deepcopy(fixture())
                data[field] = value
                with self.assertRaises(ValueError):
                    select_asset(data, TAG, NAME, SHA, REPO)


if __name__ == "__main__":
    unittest.main()
