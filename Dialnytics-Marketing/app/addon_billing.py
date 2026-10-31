"""Account-wide CRM + Power Dialer pricing policy.

Pure functions: callers must persist verified billing and entitlements separately.
Never grant access based solely on an unverified checkout request.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class CombinedAddonQuote:
    seats: int
    monthly_usd: Decimal
    enabled: bool
    billing_period_days: int = 30


def _money(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PricingError('Invalid add-on price') from exc
    if not result.is_finite() or result < 0 or result.as_tuple().exponent < -2:
        raise PricingError('Price must be a nonnegative USD amount with at most two decimals')
    return result.quantize(Decimal('0.01'))


def quote_combined_addon(seats: int, *, enabled: bool, single_price='10.00', team_price='20.00') -> CombinedAddonQuote:
    """Fixed charge for entire customer account, not per seat."""
    if type(seats) is not int or seats < 1:
        raise PricingError('Seat count must be a positive integer')
    if type(enabled) is not bool:
        raise PricingError('enabled must be boolean')
    single = _money(single_price)
    team = _money(team_price)
    return CombinedAddonQuote(seats=seats, monthly_usd=(single if seats == 1 else team) if enabled else Decimal('0.00'), enabled=enabled)


def access_allowed(*, legacy_user: bool, admin_grant: bool, addon_paid: bool, account_active: bool) -> bool:
    """Legacy accounts retain their entitlement, but suspended accounts cannot use features."""
    if any(type(v) is not bool for v in (legacy_user, admin_grant, addon_paid, account_active)):
        raise PricingError('Access flags must be boolean')
    return account_active and (legacy_user or admin_grant or addon_paid)
