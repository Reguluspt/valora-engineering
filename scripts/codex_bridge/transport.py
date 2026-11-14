"""Bounded GitHub REST protocol with injected HTTP; P1 never supplies credentials."""

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import re
import urllib.error
import urllib.parse
import urllib.request

from .schema import Rejected, canonical, parse_json

MAX_RESPONSE = 1024 * 1024
RESULT_MARKER = "VALORA_BRIDGE_OFFLINE_RESULT_V1\n"


class QueueFailure(Exception):
    def __init__(self, status=0, retry_after=None, retry_at=None):
        self.status, self.retry_after, self.retry_at = status, retry_after, retry_at


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict
    body: str


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPS:
    """Dormant adapter; no live CLI entrypoint or credential discovery in P1."""
    def __init__(self, token):
        if not isinstance(token, str) or not token or "\n" in token or "\r" in token:
            raise Rejected("CREDENTIAL_FORMAT")
        self._token = token
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def __call__(self, method, url, headers, body=None):
        parsed = urllib.parse.urlsplit(url)
        base = "/repos/Reguluspt/valora-task-queue"
        issue = re.fullmatch(re.escape(base) + r"/issues/(\d+)(/comments)?", parsed.path)
        allowed_get = parsed.path in {base, base + "/issues"} or (issue and int(issue[1]) > 1)
        allowed_post = issue and int(issue[1]) > 1 and issue[2] == "/comments"
        if parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.fragment or not (
            (method == "GET" and allowed_get) or (method == "POST" and allowed_post)
        ):
            raise Rejected("HTTP_ORIGIN")
        headers = {**headers, "Authorization": f"Bearer {self._token}"}
        request = urllib.request.Request(url, data=body.encode() if body is not None else None,
                                         headers=headers, method=method)
        try:
            try:
                response = self._opener.open(request, timeout=10)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                raw = response.read(MAX_RESPONSE + 1)
                if len(raw) > MAX_RESPONSE:
                    raise QueueFailure()
                return Response(response.code, {k.lower(): v for k, v in response.headers.items()}, raw.decode("utf-8"))
        except (OSError, UnicodeError, ValueError):
            raise QueueFailure() from None


class GitHubQueue:
    def __init__(self, policy, request, result_author_id):
        self.policy, self.request, self.result_author_id = policy, request, result_author_id
        self.root = f"https://api.github.com/repos/{policy.queue}"
        self.etag = None
        self.next_etag = None

    def call(self, method, path, body=None, extra=None):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "Content-Type": "application/json", **(extra or {})}
        try:
            result = self.request(method, self.root + path, headers, body)
        except QueueFailure:
            raise
        except Exception:
            raise QueueFailure() from None
        expected_statuses = {201} if method == "POST" else {200, 304}
        if result.status not in expected_statuses:
            retry_after, retry_at = result.headers.get("retry-after"), None
            if result.headers.get("x-ratelimit-remaining") == "0":
                try:
                    retry_at = float(result.headers["x-ratelimit-reset"])
                except (KeyError, ValueError):
                    retry_after = retry_after or "3600"
            elif result.status == 403 and "secondary rate limit" in result.body.lower():
                retry_after = retry_after or "60"
            raise QueueFailure(result.status, retry_after, retry_at)
        return result

    def repository(self):
        repo = parse_json(self.call("GET", "").body, MAX_RESPONSE)
        if not isinstance(repo, dict):
            raise QueueFailure()
        return repo

    def poll(self):
        issues = []
        self.next_etag = None
        for page in range(1, 11):
            extra = {"If-None-Match": self.etag} if self.etag and page == 1 else {}
            response = self.call("GET", f"/issues?state=open&per_page=100&page={page}&sort=created&direction=asc", extra=extra)
            if response.status == 304:
                return []
            if page == 1:
                self.next_etag = response.headers.get("etag")
            batch = parse_json(response.body, MAX_RESPONSE)
            if not isinstance(batch, list) or len(batch) > 100:
                raise QueueFailure()
            for item in batch:
                if not isinstance(item, dict) or type(item.get("number")) is not int:
                    raise QueueFailure()
                if item["number"] > 1 and "pull_request" not in item:
                    issues.append(item["number"])
            if len(batch) < 100:
                return issues
            # Page-one ETag cannot certify later pages; disable cache for pagination.
            self.next_etag = None
        raise QueueFailure()

    def issue(self, number):
        if type(number) is not int or number <= 1:
            raise Rejected("CONTROL_OR_INVALID_ISSUE")
        issue = parse_json(self.call("GET", f"/issues/{number}").body, MAX_RESPONSE)
        if not isinstance(issue, dict) or issue.get("number") != number:
            raise QueueFailure()
        return issue

    def acknowledge_poll(self):
        self.etag = self.next_etag

    def retry_poll(self):
        self.etag = None

    def publish(self, number, body):
        # Reconcile a timed-out POST by exact body and trusted result author.
        expected = RESULT_MARKER + body
        for page in range(1, 11):
            comments = parse_json(self.call("GET", f"/issues/{number}/comments?per_page=100&page={page}").body, MAX_RESPONSE)
            if not isinstance(comments, list) or len(comments) > 100:
                raise QueueFailure()
            for comment in comments:
                author = comment.get("user") if isinstance(comment, dict) else None
                if isinstance(author, dict) and author.get("id") == self.result_author_id and comment.get("body") == expected:
                    return
            if len(comments) < 100:
                self.call("POST", f"/issues/{number}/comments", canonical({"body": expected}))
                return
        raise QueueFailure()


class Backoff:
    def __init__(self):
        self.failures = 0

    def success(self):
        self.failures = 0
        return 60

    def failure(self, error, now):
        self.failures = min(self.failures + 1, 7)
        retry = 0
        if error.retry_at is not None:
            retry = max(0, error.retry_at - now)
        if error.retry_after:
            try:
                retry = max(0, int(error.retry_after))
            except (ValueError, TypeError):
                try:
                    retry = max(0, parsedate_to_datetime(error.retry_after).timestamp() - now)
                except (ValueError, TypeError, OverflowError):
                    retry = 0
        # Respect long Retry-After by postponing; a caller checks STOP while waiting.
        return max(min(60 * 2 ** self.failures, 3600), retry)
