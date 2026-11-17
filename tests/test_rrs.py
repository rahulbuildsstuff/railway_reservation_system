"""
Automated Unit, Integration, Data-Flow (All-DU-Paths) & Green SCI Test Suite
Author: Nalla Rahul (00814803124) | B.Tech (IT) 5th Sem | MAIT | CIC-357
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from rrs_engine import (
    TrainReservationEngine,
    RegretWaitlistOverflowException,
    allocate_berth_and_fare,
    compute_green_sci_score,
)


class TestUnitAndIntegrationRRS(unittest.TestCase):
    def setUp(self):
        self.engine = TrainReservationEngine("12951", "Rajdhani Exp", 1500.0, cnf_seats=4, rac_limit=2, wl_limit=2)

    def test_01_book_confirmed_berth_success(self):
        rec = self.engine.book_tickets("Nalla Rahul", 2)
        self.assertEqual(rec.status, "CNF")
        self.assertEqual(self.engine.cnf_seats, 2)

    def test_02_book_invalid_passenger_count_raises_error(self):
        with self.assertRaises(ValueError):
            self.engine.book_tickets("Invalid Pax", 7)

    def test_03_rac_allocation_when_confirmed_full(self):
        self.engine.book_tickets("Pax A", 4)
        rec = self.engine.book_tickets("Pax B", 2)
        self.assertEqual(rec.status, "RAC")

    def test_04_waitlist_overflow_exception(self):
        self.engine.book_tickets("Pax A", 4)
        self.engine.book_tickets("Pax B", 2)
        self.engine.book_tickets("Pax C", 2)
        with self.assertRaises(RegretWaitlistOverflowException):
            self.engine.book_tickets("Pax D", 1)

    def test_05_tatkal_dynamic_fare_calculation(self):
        rec = self.engine.book_tickets("Pax Tatkal", 2, quota="TATKAL")
        self.assertEqual(rec.fare_paid, 3800.0)

    def test_06_integration_cancellation_promotes_rac_to_cnf_and_wl_to_rac(self):
        eng = TrainReservationEngine("12002", "Shatabdi Exp", 1200.0, cnf_seats=1, rac_limit=1, wl_limit=1)
        t_cnf = eng.book_tickets("Pax CNF", 1)
        t_rac = eng.book_tickets("Pax RAC", 1)
        t_wl = eng.book_tickets("Pax WL", 1)
        res = eng.cancel_ticket(t_cnf.pnr_no)
        self.assertTrue(res["rac_promoted_to_cnf"])
        self.assertTrue(res["wl_promoted_to_rac"])
        self.assertEqual(eng.ledger[t_rac.pnr_no].status, "CNF")
        self.assertEqual(eng.ledger[t_wl.pnr_no].status, "RAC")

    def test_07_integration_refund_and_chart_preparation_freeze(self):
        t_cnf = self.engine.book_tickets("Nalla Rahul", 2)
        res = self.engine.cancel_ticket(t_cnf.pnr_no)
        self.assertEqual(res["refund_amount"], 2760.0)
        self.engine.prepare_final_chart()
        with self.assertRaises(RuntimeError):
            self.engine.book_tickets("Late Pax", 1)


class TestDataFlowDUPathsAndGreenSCI(unittest.TestCase):
    def test_08_du_path_invalid_pax_N1_N2_N3_N9(self):
        res = allocate_berth_and_fare(pax=0, quota="GEN", cnf=10, rac=5, base_fare=1000.0)
        self.assertEqual(res["status"], "ERR")

    def test_09_du_path_confirmed_N1_N2_N4_N5_N9(self):
        res = allocate_berth_and_fare(pax=2, quota="TATKAL", cnf=5, rac=4, base_fare=1500.0)
        self.assertEqual(res["status"], "CNF")
        self.assertEqual(res["fare"], 3800.0)

    def test_10_du_path_rac_N1_N2_N4_N6_N7_N9(self):
        res = allocate_berth_and_fare(pax=2, quota="GEN", cnf=1, rac=4, base_fare=1200.0)
        self.assertEqual(res["status"], "RAC")

    def test_11_du_path_waitlist_and_green_sci_reduction(self):
        res = allocate_berth_and_fare(pax=3, quota="GEN", cnf=1, rac=1, base_fare=1200.0)
        self.assertEqual(res["status"], "WL")
        base_sci = compute_green_sci_score(142.0, 85.0, 120.0, 420.0, 5.8)
        green_sci = compute_green_sci_score(48.5, 18.4, 43.2, 260.0, 3.2)
        self.assertLess(green_sci["sci_g_co2eq_per_1k_pnr"], base_sci["sci_g_co2eq_per_1k_pnr"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
