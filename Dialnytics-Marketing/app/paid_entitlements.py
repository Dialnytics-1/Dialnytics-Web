"""Verified billing to account-wide CRM/Power entitlement decision.

Pure policy module; never use browser-submitted flags as proof of payment.
The caller must verify payment with Stripe or an authorized manual approval.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


class EntitlementError(ValueError):
    pass


@dataclass(frozen=True)
class EntitlementDecision:
    account_id: str
    enabled: bool
    reason: str
    expires_at: Optional[datetime]


def decide_entitlement(*, account_id: str, now: datetime, legacy: bool = False,
                       admin_grant: bool = False, verified_payment: bool = False,
                       addon_purchased: bool = False, paid_through: Optional[datetime] = None,
                       account_active: bool = True) -> EntitlementDecision:
    flags = (legacy, admin_grant, verified_payment, addon_purchased, account_active)
    if any(type(flag) is not bool for flag in flags):
        raise EntitlementError('Invalid entitlement flag')
    if not isinstance(account_id, str) or not account_id.strip():
        raise EntitlementError('Account ID required')
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise EntitlementError('Timezone-aware now required')
    if paid_through is not None and (not isinstance(paid_through, datetime) or paid_through.tzinfo is None):
        raise EntitlementError('Timezone-aware paid_through required')
    if not account_active:
        return EntitlementDecision(account_id, False, 'account_inactive', paid_through)
    if legacy:
        return EntitlementDecision(account_id, True, 'legacy', None)
    if admin_grant:
        return EntitlementDecision(account_id, True, 'admin_grant', None)
    if verified_payment and addon_purchased and paid_through and paid_through > now:
        return EntitlementDecision(account_id, True, 'paid', paid_through)
    return EntitlementDecision(account_id, False, 'not_entitled', paid_through)
