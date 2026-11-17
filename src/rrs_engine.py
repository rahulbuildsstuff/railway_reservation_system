"""
Full-Featured Railway Reservation System (RRS) Engine with SQLite3 Persistence & Interactive CLI
Student: Nalla Rahul (00814803124) | B.Tech (IT) 5th Sem | MAIT | CIC-357
"""
import os
import sqlite3
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional


class RegretWaitlistOverflowException(Exception):
    """Raised when Confirmed, RAC, and Waitlist quotas are all exhausted."""
    pass


@dataclass
class TicketRecord:
    pnr_no: str
    train_no: str
    pax_name: str
    pax_count: int
    coach_class: str
    quota: str
    status: str
    berth_label: str
    fare_paid: float
    refund_amount: float = 0.0


class TrainReservationEngine:
    """ACID-compliant Railway Reservation, Cancellation & RAC/WL Auto-Promotion Engine."""

    CLASS_MULTIPLIERS = {"3A": 1.0, "2A": 1.45, "1A": 2.25, "SL": 0.45}

    def __init__(self, train_no: str = "12951", train_name: str = "New Delhi - Mumbai Rajdhani Exp",
                 base_fare: float = 1500.0, cnf_seats: int = 6, rac_limit: int = 2, wl_limit: int = 3,
                 db_path: str = ":memory:"):
        self.train_no = train_no
        self.train_name = train_name
        self.base_fare = base_fare
        self.cnf_seats = cnf_seats
        self.rac_limit = rac_limit
        self.wl_limit = wl_limit
        self.rac_booked = 0
        self.wl_booked = 0
        self.chart_prepared = False
        self.pnr_counter = 2489104500
        self.ledger: Dict[str, TicketRecord] = {}
        self.conn = sqlite3.connect(db_path)
        self._init_sqlite_schema()

    def _init_sqlite_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS PNR_Ledger (
                pnr_no TEXT PRIMARY KEY,
                train_no TEXT,
                pax_name TEXT,
                pax_count INTEGER,
                coach_class TEXT,
                quota TEXT,
                status TEXT,
                berth_label TEXT,
                fare_paid REAL,
                refund_amount REAL
            )
        """)
        self.conn.commit()

    def _sync_record_to_db(self, rec: TicketRecord) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO PNR_Ledger
            (pnr_no, train_no, pax_name, pax_count, coach_class, quota, status, berth_label, fare_paid, refund_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rec.pnr_no, rec.train_no, rec.pax_name, rec.pax_count, rec.coach_class,
              rec.quota, rec.status, rec.berth_label, rec.fare_paid, rec.refund_amount))
        self.conn.commit()

    def book_tickets(self, pax_name: str, pax_count: int,
                     coach_class: str = "3A", quota: str = "GENERAL",
                     berth_pref: str = "LB") -> TicketRecord:
        if self.chart_prepared:
            raise RuntimeError("Reservation chart is already prepared; booking is frozen.")
        if pax_count < 1 or pax_count > 6:
            raise ValueError("Passenger count per PNR must be between 1 and 6")

        if self.cnf_seats >= pax_count:
            start_seat = self.cnf_seats
            self.cnf_seats -= pax_count
            status = "CNF"
            berth_label = f"Coach B4 - Berth {start_seat} ({berth_pref})"
        elif (self.rac_limit - self.rac_booked) >= pax_count:
            self.rac_booked += pax_count
            status = "RAC"
            berth_label = f"Coach B4 - SL Shared (RAC-{self.rac_booked})"
        elif (self.wl_limit - self.wl_booked) >= pax_count:
            self.wl_booked += pax_count
            status = "WL"
            berth_label = f"Waitlist WL-{self.wl_booked}"
        else:
            raise RegretWaitlistOverflowException("REGRET: Waitlist quota exhausted")

        mult = self.CLASS_MULTIPLIERS.get(coach_class.upper(), 1.0)
        tatkal_surcharge = 400.0 if quota.upper() == "TATKAL" else 0.0
        unit_fare = (self.base_fare * mult) + tatkal_surcharge
        if quota.upper() == "SENIOR":
            unit_fare *= 0.80
        total_fare = round(pax_count * unit_fare, 2)

        self.pnr_counter += 1
        pnr_no = str(self.pnr_counter)
        record = TicketRecord(
            pnr_no=pnr_no,
            train_no=self.train_no,
            pax_name=pax_name,
            pax_count=pax_count,
            coach_class=coach_class.upper(),
            quota=quota.upper(),
            status=status,
            berth_label=berth_label,
            fare_paid=total_fare
        )
        self.ledger[pnr_no] = record
        self._sync_record_to_db(record)
        return record

    def cancel_ticket(self, pnr_no: str) -> Dict[str, object]:
        if pnr_no not in self.ledger:
            raise KeyError(f"PNR {pnr_no} not found")
        rec = self.ledger[pnr_no]
        if rec.status == "CANCELLED":
            raise ValueError("Ticket is already cancelled")

        pax_count = rec.pax_count
        old_status = rec.status
        freed_berth = rec.berth_label
        rec.status = "CANCELLED"
        rec.berth_label = "Cancelled & Refunded"
        rec.refund_amount = round(max(0.0, rec.fare_paid - (120.0 * pax_count)), 2)
        self._sync_record_to_db(rec)

        rac_promoted = False
        wl_promoted = False

        if old_status == "CNF":
            if self.rac_booked >= pax_count:
                self.rac_booked -= pax_count
                rac_promoted = True
                for r in self.ledger.values():
                    if r.status == "RAC":
                        r.status = "CNF"
                        r.berth_label = f"Promoted to CNF ({freed_berth})"
                        self._sync_record_to_db(r)
                        break
                if self.wl_booked >= pax_count:
                    self.wl_booked -= pax_count
                    self.rac_booked += pax_count
                    wl_promoted = True
                    for w in self.ledger.values():
                        if w.status == "WL":
                            w.status = "RAC"
                            w.berth_label = "Promoted to RAC (Shared SL)"
                            self._sync_record_to_db(w)
                            break
            else:
                self.cnf_seats += pax_count

        return {
            "pnr_no": pnr_no,
            "rac_promoted_to_cnf": rac_promoted,
            "wl_promoted_to_rac": wl_promoted,
            "refund_amount": rec.refund_amount
        }

    def prepare_final_chart(self) -> int:
        """Freezes bookings and auto-cancels remaining WL tickets with 100% refund."""
        self.chart_prepared = True
        auto_cancelled = 0
        for rec in self.ledger.values():
            if rec.status == "WL":
                rec.status = "CANCELLED"
                rec.refund_amount = rec.fare_paid
                rec.berth_label = "Auto-Cancelled at Chart Prep (Full Refund)"
                self._sync_record_to_db(rec)
                auto_cancelled += 1
        self.wl_booked = 0
        return auto_cancelled


def allocate_berth_and_fare(pax: int, quota: str, cnf: int, rac: int, base_fare: float) -> dict:
    """Data-Flow Testing target function (Experiment 14) with annotated CFG nodes N1..N9."""
    # Node N1: Parameter definitions def(pax, quota, cnf, rac, base_fare)
    # Node N2: Predicate use p-use(pax)
    if pax < 1 or pax > 6:
        # Node N3: Invalid passenger count branch
        status = "ERR"
        fare = 0.0
    else:
        # Node N4: Predicate use p-use(cnf, pax)
        if cnf >= pax:
            # Node N5: Confirmed allocation c-use & re-definition
            cnf = cnf - pax
            status = "CNF"
            fare = pax * (base_fare + (400.0 if quota == "TATKAL" else 0.0))
        # Node N6: Predicate use p-use(rac, pax)
        elif rac >= pax:
            # Node N7: RAC allocation c-use & re-definition
            rac = rac - pax
            status = "RAC"
            fare = pax * base_fare
        else:
            # Node N8: Waitlist fallback
            status = "WL"
            fare = pax * base_fare
    # Node N9: Computational use c-use(status, fare, cnf, rac)
    return {"status": status, "fare": fare, "cnf_rem": cnf, "rac_rem": rac}


def compute_green_sci_score(cpu_wh: float, net_mb: float, storage_gb: float,
                            grid_ci: float, embodied_g: float) -> dict:
    """ISO/IEC 21031 Software Carbon Intensity (SCI) Evaluator (Experiment 15)."""
    total_kwh = (cpu_wh + (net_mb * 0.06) + (storage_gb * 0.02)) / 1000.0
    sci_g = (total_kwh * grid_ci) + embodied_g
    return {
        "energy_wh_per_1k_pnr": round(total_kwh * 1000.0, 2),
        "sci_g_co2eq_per_1k_pnr": round(sci_g, 2)
    }


def run_demo_simulation() -> None:
    print("=" * 80)
    print("  RAILWAY RESERVATION SYSTEM (RRS) - FULL FUNCTIONAL ENGINE SIMULATION")
    print("  Student: Nalla Rahul (00814803124) | B.Tech IT 5th Sem | MAIT (CIC-357)")
    print("=" * 80)
    engine = TrainReservationEngine("12951", "New Delhi - Mumbai Rajdhani Exp", 1500.0, cnf_seats=2, rac_limit=1, wl_limit=1)

    t1 = engine.book_tickets("Nalla Rahul", 1, "3A", "GENERAL", "LB")
    t1b = engine.book_tickets("Sidharth Nalla", 1, "3A", "GENERAL", "MB")
    print(f"[1. BOOK CNF] PNR={t1.pnr_no} ({t1.pax_name}) & PNR={t1b.pnr_no} ({t1b.pax_name}) | Status={t1.status} | {t1.berth_label} | Rs.{t1.fare_paid}")

    t2 = engine.book_tickets("Aman Verma", 1, "3A", "TATKAL", "SL")
    print(f"[2. BOOK RAC] PNR={t2.pnr_no} | Pax={t2.pax_name} (1) | Status={t2.status} | {t2.berth_label} | Rs.{t2.fare_paid}")

    t3 = engine.book_tickets("Sujal Sharma", 1, "3A", "GENERAL", "UB")
    print(f"[3. BOOK WL ] PNR={t3.pnr_no} | Pax={t3.pax_name} (1) | Status={t3.status} | {t3.berth_label} | Rs.{t3.fare_paid}")

    c_res = engine.cancel_ticket(t1.pnr_no)
    print(f"[4. CANCEL  ] Cancelled PNR={t1.pnr_no} | Refund=Rs.{c_res['refund_amount']} | RAC->CNF={c_res['rac_promoted_to_cnf']} | WL->RAC={c_res['wl_promoted_to_rac']}")
    print(f"    -> Updated PNR {t2.pnr_no} ({t2.pax_name}): Status={engine.ledger[t2.pnr_no].status} [{engine.ledger[t2.pnr_no].berth_label}]")
    print(f"    -> Updated PNR {t3.pnr_no} ({t3.pax_name}): Status={engine.ledger[t3.pnr_no].status} [{engine.ledger[t3.pnr_no].berth_label}]")
    print("=" * 80)


if __name__ == "__main__":
    run_demo_simulation()
