"""Business logic for the contracts app.

Three service modules:

* ``numbering`` — atomic allocation of per-project contract numbers.
* ``transitions`` — the Contract.action state machine and its side-effects.
* ``schedule`` — deterministic PaymentSchedule generation from Calculation.

All of these are called **explicitly** from ViewSet actions / management
commands. There are no signals.
"""
