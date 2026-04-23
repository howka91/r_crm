"""Contracts models — package entry point.

Follows the convention established by `apps.references.models` and
`apps.clients.models`: one file per substantive model, re-exported here so
`from apps.contracts.models import Contract` keeps working.
"""
from apps.contracts.models.contract import Contract
from apps.contracts.models.contract_template import ContractTemplate
from apps.contracts.models.payment import Payment
from apps.contracts.models.payment_schedule import PaymentSchedule

__all__ = [
    "Contract",
    "ContractTemplate",
    "PaymentSchedule",
    "Payment",
]
