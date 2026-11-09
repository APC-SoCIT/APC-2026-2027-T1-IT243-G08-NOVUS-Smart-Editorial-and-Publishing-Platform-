"""NFR-02: an assessment answers within 30 seconds or the article goes to
manual review. These run the real evaluation service against a stand-in for
the model client, so the timeout path is exercised end to end."""
import httpx
import anthropic
import pytest
 
from apps.editorial.models import Article
from tests.test_editorial_flow import draft_payload
 
 
class SlowClient:
    """Stands in for anthropic.Anthropic and times out like it would."""
    made_with = {}
 
    def __init__(self, **kwargs):
        SlowClient.made_with = kwargs
        self.messages = self
 
    def create(self, **kwargs):
        raise anthropic.APITimeoutError(
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
 
 
@pytest.fixture
def slow_model(settings, monkeypatch):
    from apps.ai_eval import services
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    monkeypatch.setattr("apps.ai_eval.services.anthropic.Anthropic", SlowClient)
    # conftest stubs the evaluator for every test; this one needs the real one.
    monkeypatch.setattr("apps.editorial.views.evaluate_article", services.evaluate_article)
 
 
@pytest.mark.django_db
class TestAssessmentTimeLimit:
    def test_the_client_has_a_hard_limit_and_no_retries(self, settings, slow_model):
        from apps.ai_eval.services import evaluate_article
        settings.AI_TIMEOUT_SECONDS = 25
        with pytest.raises(anthropic.APITimeoutError):
            evaluate_article(Article(title="t", body="<p>b</p>"))
        assert SlowClient.made_with["timeout"] == 25
        assert SlowClient.made_with["max_retries"] == 0
 
    def test_a_timeout_sends_the_article_to_review(self, auth_client, writer, slow_model):
        c = auth_client(writer)
        aid = c.post("/api/editorial/articles/", draft_payload("Slow model"), format="json").data["id"]
        r = c.post(f"/api/editorial/articles/{aid}/submit/")
        assert r.data["gate"] == "BYPASSED"
        a = Article.objects.get(pk=aid)
        assert a.status == Article.Status.UNDER_REVIEW
        assert a.returned_by_ai is False
        assert not a.evaluations.exists()
 
 
def test_the_web_worker_outlasts_the_assessment(settings):
    import runpy
    from pathlib import Path
    conf = runpy.run_path(str(Path(__file__).resolve().parents[1] / "gunicorn.conf.py"))
    assert conf["timeout"] > settings.AI_TIMEOUT_SECONDS + 5
