"""Managed categories: an editor can add one from the picker, and an
article's category must come from the list."""
import pytest

from apps.accounts.models import User
from apps.editorial import categories
from apps.editorial.models import Article, Category

URL = "/api/editorial/categories/"


@pytest.mark.django_db
class TestCategoryList:
    def test_the_five_starting_sections_exist(self, auth_client, editor):
        names = [c["name"] for c in auth_client(editor).get(URL).json()]
        assert {"Business", "Tech", "Life", "Innovation", "Leadership"} <= set(names)

    def test_archived_ones_are_left_out_of_the_pickers(self, auth_client, writer):
        Category.objects.filter(name="Life").update(is_active=False)
        names = [c["name"] for c in auth_client(writer).get(URL).json()]
        assert "Life" not in names

    def test_readers_cannot_list_them(self, auth_client, make_user):
        reader = make_user("r@boss.ph", User.Role.READER)
        assert auth_client(reader).get(URL).status_code == 403


@pytest.mark.django_db
class TestCreateCategory:
    def test_an_editor_creates_one(self, auth_client, editor):
        r = auth_client(editor).post(URL, {"name": "  Food   and Drink "}, format="json")
        assert r.status_code == 201 and r.json()["name"] == "Food and Drink"
        assert Category.objects.get(name="Food and Drink").created_by == editor

    def test_an_existing_name_is_handed_back_not_duplicated(self, auth_client, editor):
        r = auth_client(editor).post(URL, {"name": "tech"}, format="json")
        assert r.status_code == 200 and r.json()["name"] == "Tech"
        assert Category.objects.filter(name__iexact="tech").count() == 1

    def test_an_archived_name_is_refused(self, auth_client, editor):
        Category.objects.filter(name="Life").update(is_active=False)
        assert auth_client(editor).post(URL, {"name": "life"}, format="json").status_code == 409

    @pytest.mark.parametrize("name", ["", "x", "a" * 41, "<script>"])
    def test_bad_names_are_refused(self, auth_client, editor, name):
        assert auth_client(editor).post(URL, {"name": name}, format="json").status_code == 400

    def test_a_writer_cannot_create_one(self, auth_client, writer):
        assert auth_client(writer).post(URL, {"name": "Travel"}, format="json").status_code == 403


@pytest.mark.django_db
class TestArticleCategory:
    def assign(self, client, writer, category):
        return client.post("/api/editorial/articles/assign/", {
            "title": "Port congestion", "writer": writer.pk, "category": category,
        }, format="json")

    def test_assigning_uses_the_stored_spelling(self, auth_client, editor, writer):
        r = self.assign(auth_client(editor), writer, "business")
        assert r.status_code == 201
        assert Article.objects.get().category == "Business"

    def test_an_unknown_category_is_refused(self, auth_client, editor, writer):
        r = self.assign(auth_client(editor), writer, "Astrology")
        assert r.status_code == 400 and "category" in r.json()

    def test_an_article_keeps_an_archived_category_when_saved(self, auth_client, writer):
        a = Article.objects.create(writer=writer, title="T", body="", category="Life",
                                   status=Article.Status.DRAFTING)
        Category.objects.filter(name="Life").update(is_active=False)
        r = auth_client(writer).patch(f"/api/editorial/articles/{a.pk}/",
                                      {"category": "Life", "title": "T2"}, format="json")
        assert r.status_code == 200

    def test_renaming_moves_the_articles(self, writer):
        a = Article.objects.create(writer=writer, title="T", body="", category="Tech")
        categories.rename(Category.objects.get(name="Tech"), "Technology")
        a.refresh_from_db()
        assert a.category == "Technology"
