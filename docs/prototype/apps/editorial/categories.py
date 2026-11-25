"""Managed categories: how a typed name is cleaned, checked and renamed.

One place for the rules, so the assign form, the compose page and the
admin site all agree on what counts as the same category.
"""
import re

from django.db import transaction
from rest_framework import serializers

from .models import Article, Category

NAME_RE = re.compile(r"^[\w][\w &'\-/]*$", re.UNICODE)


def normalise(name):
    """Trim and collapse spaces: "  Food   and drink " → "Food and drink"."""
    return " ".join((name or "").split())


def validate_new_name(name):
    name = normalise(name)
    if not 2 <= len(name) <= 40:
        raise serializers.ValidationError("A category name is 2 to 40 characters.")
    if not NAME_RE.match(name):
        raise serializers.ValidationError(
            "Use letters, numbers, spaces and & ' - / only.")
    return name


def find(name):
    """The category with this name, ignoring case, or None."""
    return Category.objects.filter(name__iexact=normalise(name)).first()


def clean_article_category(value, current=""):
    """What an article's category field may hold: blank, an active category
    (returned in its stored spelling), or the value it already has, so an
    article filed under a since-archived category can still be saved."""
    value = normalise(value)
    if not value:
        return ""
    if current and value == current:
        return value
    cat = find(value)
    if cat is None or not cat.is_active:
        raise serializers.ValidationError(
            "Choose a category from the list, or ask an editor to create it.")
    return cat.name


@transaction.atomic
def rename(category, new_name):
    """Rename a category and every article filed under the old name."""
    old = category.name
    category.name = new_name
    category.save(update_fields=["name", "updated_at"])
    if old != new_name:
        Article.objects.filter(category=old).update(category=new_name)
    return category
