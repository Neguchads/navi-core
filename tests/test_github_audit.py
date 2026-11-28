"""Offline tests: fake transport only, no account access or remote writes."""
import unittest
from navi_core.github_audit import AuditError, inventory, pages


class PortfolioTests(unittest.TestCase):
    def test_scope_and_no_mutation(self):
        requests = []
        def repo(i, name, owner="alice", fork=False, archived=False):
            return dict(id=i, name=name, owner={"login": owner}, fork=fork, archived=archived)
        def get(path):
            requests.append(path)
            endpoint = path.split("?")[0]
            if endpoint == "user":
                return {"login": "Alice"}
            if endpoint == "user/repos":
                return [repo(1, "active"), repo(2, "fork", fork=True),
                        repo(3, "archive", archived=True), repo(4, "other", owner="team")]
            if endpoint == "repos/alice/active/issues":
                return [{"id": 1, "number": 1}, {"id": 2, "number": 2},
                        {"id": 3, "number": 3, "pull_request": {}}]
            if endpoint == "repos/alice/active/issues/1/comments":
                return [{"id": 4, "user": {"login": "alice"}, "body": "Reviewed"}]
            if endpoint == "repos/alice/active/issues/2/comments":
                return [{"id": 5, "user": {"login": "someone"}, "body": "Hello"}]
            if endpoint == "repos/alice/active/pulls":
                return [{"id": 3, "number": 3}]
            if endpoint == "repos/alice/active/pulls/3":
                return {"number": 3, "head": {"sha": "a"*40}, "base": {"sha": "b"*40},
                        "draft": False, "mergeable": True}
            self.fail("Unexpected endpoint")
        result = inventory(get, owner="Alice")
        self.assertTrue(result["complete"])
        self.assertEqual(result["excluded"], 3)
        self.assertEqual(result["writes_performed"], 0)
        active, = result["repositories"]
        self.assertEqual(active["repository"], "alice/active")
        self.assertEqual([i["owner_comment_observed"] for i in active["issues"]], [True, False])
        self.assertEqual(active["pull_requests"][0]["disposition"], "blocked_pending_full_review")
        self.assertTrue(all("fork/" not in x and "archive/" not in x for x in requests))

    def test_identity_mismatch_blocks(self):
        with self.assertRaises(AuditError):
            inventory(lambda _: {"login": "other"}, owner="alice")

    def test_pagination_and_duplicate_detection(self):
        def get(path):
            return [{"id": i} for i in range(100)] if path.endswith("page=1") else [{"id": 100}]
        self.assertEqual(len(list(pages(get, "items"))), 101)
        with self.assertRaises(AuditError):
            list(pages(lambda _: [{"id": i} for i in range(100)], "items"))

    def test_failed_repository_is_incomplete(self):
        def get(path):
            if path == "user":
                return {"login": "alice"}
            if path.startswith("user/repos?"):
                return [{"id": 1, "name": "active", "owner": {"login": "alice"},
                         "fork": False, "archived": False}]
            raise AuditError("missing permission")
        report = inventory(get, owner="alice")
        self.assertFalse(report["complete"])
        self.assertEqual(report["repositories"][0]["status"], "incomplete")

    def test_unknown_fork_status_blocks(self):
        def get(path):
            return {"login": "alice"} if path == "user" else [
                {"id": 1, "name": "unknown", "owner": {"login": "alice"}, "archived": False}]
        with self.assertRaises(AuditError):
            inventory(get, owner="alice")


if __name__ == "__main__":
    unittest.main()
