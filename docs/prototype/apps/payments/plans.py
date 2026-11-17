"""
The subscription plans (UC-4.3).

Subscriptions are prepaid: each payment buys a fixed period of access, and
nothing is charged automatically. Automatic renewal works with cards only,
while most readers pay with GCash or Maya, which cannot be charged without
the reader approving each payment. A reminder before the
period ends (see subscription_upkeep) and a one-click renewal take the place
of an automatic charge.

Prices are in centavos, the smallest unit of the peso, so that money is never
held as a decimal fraction.
"""
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    amount: int          # centavos
    days: int
    note: str = ""

    @property
    def length(self):
        return timedelta(days=self.days)

    @property
    def price(self):
        return f"₱{self.amount // 100:,}"

    def as_dict(self):
        return {"code": self.code, "name": self.name, "amount": self.amount,
                "price": self.price, "days": self.days, "note": self.note}


MONTHLY = Plan("MONTHLY", "Monthly", 19_900, 30)
ANNUAL = Plan("ANNUAL", "Annual", 199_000, 365, note="Best value: two months free")

PLANS = {p.code: p for p in (MONTHLY, ANNUAL)}
CURRENCY = "PHP"
