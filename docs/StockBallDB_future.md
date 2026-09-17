# StockBallDB — Future / Deferred Ideas

**Purpose:** Parking area for ideas deliberately deferred beyond StockBallDB V2.  
**Companion docs:** [index](StockBallDB_index.md) · [V2 scope](StockBallDB_V2_scope.md) · [V2 decisions](StockBallDB_V2_decisions.md) · [manifesto](StockBallDB_manifesto.md)

**Deferred does not mean rejected or promised.**

This document exists to:

1. keep good ideas from being lost; and
2. stop future / research functionality from quietly creeping into V2.

It is **not** a V3 specification. Do not design a full future research architecture here.

Authoritative V2 boundary: [StockBallDB_V2_scope.md](StockBallDB_V2_scope.md).

---

## Research / experiments

Work that evaluates whether something in StockBallDB predicts or explains something else.

**Seeded boundary example (excluded from V2):**

> When SPY falls more than 3%, what happens over the following 5, 10, or 20 trading days?

That question uses stored history to study a relationship / outcome pattern. V2 may filter dates where `SPY return_1d < -0.03`, but must not turn that filter into an experiment engine.

Related deferred themes:

* hypothesis testing over canonical fields;
* event studies and conditional outcome summaries;
* exploratory correlation discovery aimed at predictive relationships;
* research notebooks / experiment runners consuming StockBallDB.

The manifesto’s future research environment concept (historically referred to as MoneyBallApp) belongs in this deferred research space, not in V2 scope.

---

## Prediction / modelling

* predictive modelling;
* machine-learning training on StockBallDB features;
* expected-return or probability-of-rise tools;
* forecasts presented as product features.

---

## Strategy / backtesting

* strategy construction;
* rule backtesting;
* signal generation;
* “best setup” discovery;
* security ranking intended to pick winners.

---

## Portfolio / trading functionality

* portfolio construction;
* optimization;
* position sizing;
* P&L simulation;
* buy / sell recommendations;
* trading decisions or order workflows.

---

## Other deferred application ideas

Capture additional out-of-V2 product ideas here as they arise. Keep entries short.

| Idea | Notes | Status |
| ---- | ----- | ------ |
| _(none additional yet)_ | Use this table for later parking-lot entries | Deferred |

---

## How to use this document

* If an idea fails the V2 decision test in the scope doc, record it here instead of stretching V2.
* Do not implement parked ideas “a little bit” inside V2 UI without an explicit scope change and decision-log update.
* Promoting a deferred idea into an active version requires a deliberate later decision — not silent scope drift.
