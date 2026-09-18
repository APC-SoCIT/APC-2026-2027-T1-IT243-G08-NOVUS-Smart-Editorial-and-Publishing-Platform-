"""
Who may read paid content.

The check lived in three places and was about to live in four. Centralising it
means the paywall cannot come to mean different things on the article page, the
issue page and the download endpoint.
"""


def is_entitled(user):
    """True where the user may read subscriber-only content in full.

    Staff pass outright. The paywall exists to monetise readers, not to
    obstruct the people producing the magazine: an editor checking how their
    published article reads, or a designer confirming the cover renders, is
    doing their job, and a public-site link that shows them a subscription
    notice is useless for the purpose it exists for.

    They pass by role rather than by being granted a subscriber tier, which
    would put staff accounts into the revenue figures and make the subscriber
    count wrong.
    """
    if not user or not user.is_authenticated:
        return False

    if getattr(user, "is_suspended", False):
        return False

    # Every role except READER is staff.
    if getattr(user, "role", None) and user.role != user.Role.READER:
        return True

    profile = getattr(user, "reader_profile", None)
    return bool(profile and profile.tier == profile.Tier.SUBSCRIBER)
