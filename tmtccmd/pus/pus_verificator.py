import enum
from dataclasses import dataclass
from typing import Dict, Optional

from spacepackets.ecss import PusTelecommand
from spacepackets.ecss.pus_1_verification import RequestId, Service1Tm, Subservices


class StatusField(enum.IntEnum):
    UNSET = -1
    FAILURE = 0
    SUCCESS = 1


@dataclass
class VerificationStatus:
    all_verifs_recvd: bool
    accepted: StatusField
    started: StatusField
    step: int
    completed: StatusField


VerifDictT = Dict[RequestId, VerificationStatus]


@dataclass
class TmCheckResult:
    """Result type for a TM check.

    Special note on the completed flag: This flag indicates that
    any of the steps have failed or there was a completion success. This does not mean that
    all related verification packets have been received for the respective telecommand. If all
    packets were received, the :py:attr:`VerificationStatus.all_verifs_recvd` field will bet
    set to True
    """

    req_id_in_dict: bool
    status: Optional[VerificationStatus]
    completed: bool


class PusVerificator:
    def __init__(self):
        self._verif_dict: VerifDictT = dict()
        pass

    def add_tc(self, tc: PusTelecommand) -> bool:
        req_id = RequestId.from_sp_header(tc.sp_header)
        if req_id in self._verif_dict:
            return False
        self._verif_dict.update(
            {
                req_id: VerificationStatus(
                    all_verifs_recvd=False,
                    accepted=StatusField.UNSET,
                    started=StatusField.UNSET,
                    step=0,
                    completed=StatusField.UNSET,
                )
            }
        )
        return True

    def add_tm(self, pus_1_tm: Service1Tm) -> TmCheckResult:
        req_id = pus_1_tm.tc_req_id
        res = TmCheckResult(False, None, False)
        if req_id not in self._verif_dict:
            return res
        res.req_id_in_dict = True
        verif_status = self._verif_dict.get(req_id)
        if pus_1_tm.subservice <= 0 or pus_1_tm.subservice > 8:
            raise ValueError(
                f"PUS 1 TM with invalid subservice {pus_1_tm.subservice} was passed"
            )
        res.status = verif_status
        if pus_1_tm.subservice % 2 == 0:
            # For failures, verification handling is completed
            res.completed = True
        if pus_1_tm.subservice == Subservices.TM_ACCEPTANCE_SUCCESS:
            verif_status.accepted = StatusField.SUCCESS
        elif pus_1_tm.subservice == Subservices.TM_ACCEPTANCE_FAILURE:
            verif_status.all_verifs_recvd = True
            verif_status.accepted = StatusField.FAILURE
            res.completed = True
        elif pus_1_tm.subservice == Subservices.TM_START_SUCCESS:
            verif_status.started = StatusField.SUCCESS
        elif pus_1_tm.subservice == Subservices.TM_START_FAILURE:
            res.completed = True
            if verif_status.accepted != StatusField.UNSET:
                verif_status.all_verifs_recvd = True
            verif_status.started = StatusField.FAILURE
        elif pus_1_tm.subservice == Subservices.TM_STEP_SUCCESS:
            verif_status.step = pus_1_tm.step_id
        elif pus_1_tm.subservice == Subservices.TM_STEP_FAILURE:
            self._check_all_replies_recvd_after_step(verif_status)
            verif_status.step = -1
            res.completed = True
        elif pus_1_tm.subservice == Subservices.TM_COMPLETION_SUCCESS:
            self._check_all_replies_recvd_after_step(verif_status)
            verif_status.completed = StatusField.SUCCESS
            res.completed = True
        elif pus_1_tm.subservice == Subservices.TM_COMPLETION_FAILURE:
            self._check_all_replies_recvd_after_step(verif_status)
            verif_status.completed = StatusField.FAILURE
            res.completed = True
        return res

    @property
    def verif_dict(self):
        return self._verif_dict

    @staticmethod
    def _check_all_replies_recvd_after_step(verif_stat: VerificationStatus):
        if (
            verif_stat.accepted != StatusField.UNSET
            and verif_stat.started != StatusField.UNSET
        ):
            verif_stat.all_verifs_recvd = True

    def remove_completed_entries(self):
        self._verif_dict = {
            key: val for key, val in self._verif_dict.items() if val.all_verifs_recvd
        }

    def remove_entry(self, req_id: RequestId) -> bool:
        if req_id in self._verif_dict:
            del self._verif_dict[req_id]
            return True
        return False