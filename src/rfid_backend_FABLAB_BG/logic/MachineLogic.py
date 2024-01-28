""" This module contains the MachineLogic class. """

import logging

from time import time

from rfid_backend_FABLAB_BG.mqtt.mqtt_types import MachineResponse, SimpleResponse, UserResponse
from rfid_backend_FABLAB_BG.database.DatabaseBackend import DatabaseBackend
from rfid_backend_FABLAB_BG.database.constants import DEFAULT_TIMEOUT_MINUTES, USER_LEVEL


class MachineLogic:
    """
    The MachineLogic class represents the logic for interacting with a machine in the system.
    It provides methods for checking the machine status, handling machine alive messages,
    authorizing users, starting and ending machine use, and registering maintenance interventions.
    """

    database: DatabaseBackend = None

    def __init__(self, machine_id):
        """
        Initializes a new instance of the MachineLogic class.

        Args:
            machine_id (int): The ID of the machine.

        Raises:
            Exception: If the database is not initialized.
            Exception: If the machine ID is invalid.
        """
        self._machine_id = machine_id
        self._last_alive = 0

        if MachineLogic.database is None:
            raise ValueError("Database not initialized")

        with self.database.getSession() as session:
            machine_repo = MachineLogic.database.getMachineRepository(session)
            if machine_repo.get_by_id(machine_id) is None:
                raise ValueError("Invalid machine id")

        logging.info(f"Machine logic instance for ID:{machine_id} initialized")

    def updateMachineLastSeen(self):
        """
        Updates the last seen timestamp of the machine.
        """
        self._last_alive = time()
        try:
            with MachineLogic.database.getSession() as session:
                machine_repo = MachineLogic.database.getMachineRepository(session)
                machine = machine_repo.get_by_id(self._machine_id)
                machine.last_seen = time()
                machine_repo.update(machine)
        except Exception as e:
            logging.error("updateMachineLastSeen exception %s", str(e), exc_info=True)

    def machineStatus(self):
        """
        Gets the status of the machine.

        Returns:
            MachineResponse: The machine response object containing the status information.
        """
        try:
            with MachineLogic.database.getSession() as session:
                machine_repo = MachineLogic.database.getMachineRepository(session)
                machine = machine_repo.get_by_id(self._machine_id)
                if machine is None:
                    return MachineResponse(True, False, False, False, "?", 0, DEFAULT_TIMEOUT_MINUTES)
                self.updateMachineLastSeen()
                return MachineResponse(
                    True,
                    True,
                    machine_repo.getMachineMaintenanceNeeded(machine.machine_id)[0],
                    not machine.blocked,
                    machine.machine_name,
                    machine.machine_type_id,
                    machine.machine_type.type_timeout_min,
                )
        except Exception as e:
            logging.error("machineStatus exception %s", str(e), exc_info=True)
            return MachineResponse(False, False, False, False, "?", 0, DEFAULT_TIMEOUT_MINUTES)

    def machineAlive(self):
        """
        Called when a machine sends an alive message.
        """
        logging.debug(f"Machine {self._machine_id} alive")
        self.updateMachineLastSeen()

    def isAuthorized(self, card_uuid: str) -> UserResponse:
        """
        Checks if a user is authorized to use the machine.

        Args:
            card_uuid (str): The UUID of the user's card.

        Returns:
            UserResponse: The user response object containing the authorization information.
        """
        try:
            self.updateMachineLastSeen()
            with MachineLogic.database.getSession() as session:
                machine_repo = MachineLogic.database.getMachineRepository(session)
                user_repo = MachineLogic.database.getUserRepository(session)
                user = user_repo.getUserByCardUUID(card_uuid)
                machine = machine_repo.get_by_id(self._machine_id)
                if user is None and machine is not None:
                    unknown_repo = MachineLogic.database.getUnknownCardRepository(session)
                    unknown_repo.registerUnknownCard(card_uuid, machine.machine_id)
                
                if machine is None or user is None:
                    return UserResponse(True, False, "Unknown", USER_LEVEL.INVALID, False)
                if user_repo.IsUserAuthorizedForMachine(machine, user):
                    return UserResponse(True, True, user.name, user.user_level(), False)
                else:
                    return UserResponse(True, False, "User not authorized", USER_LEVEL.INVALID, True)

        except Exception as e:
            logging.error("isAuthorized exception %s", str(e), exc_info=True)
            return UserResponse(False, False, "", USER_LEVEL.INVALID, True)

    def startUse(self, card_uuid: str) -> SimpleResponse:
        """
        Starts the use of the machine by a user.

        Args:
            card_uuid (str): The UUID of the user's card.

        Returns:
            SimpleResponse: The simple response object indicating the success or failure of the operation.
        """
        try:
            self.updateMachineLastSeen()
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Invalid card")

                use_repo = MachineLogic.database.getUseRepository(session)
                result = use_repo.startUse(self._machine_id, user, time())

                return SimpleResponse(result, "")
        except Exception as e:
            logging.error("startUse exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")

    def inUse(self, card_uuid: str, duration_s: int) -> SimpleResponse:
        """
        Update current usage of the machine by a user.

        Args:
            card_uuid (str): The UUID of the user's card.
            duration_s (int): The duration of the machine use in seconds.

        Returns:
            SimpleResponse: The simple response object indicating the success or failure of the operation.
        """
        try:
            self.updateMachineLastSeen()
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Invalid card")

                use_repo = MachineLogic.database.getUseRepository(session)
                result = use_repo.inUse(self._machine_id, user, duration_s)

                return SimpleResponse(result, "inUse")
        except Exception as e:
            logging.error("inuse exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")

    def endUse(self, card_uuid: str, duration_s: int) -> SimpleResponse:
        """
        Ends the use of the machine by a user.

        Args:
            card_uuid (str): The UUID of the user's card.
            duration_s (int): The duration of the machine use in seconds.

        Returns:
            SimpleResponse: The simple response object indicating the success or failure of the operation.
        """
        try:
            self.updateMachineLastSeen()
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Invalid card")

                use_repo = MachineLogic.database.getUseRepository(session)
                duration_s = use_repo.endUse(self._machine_id, user, duration_s)

                return SimpleResponse(True, f"Duration {duration_s} seconds")
        except Exception as e:
            logging.error("enduse exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")

    def registerMaintenance(self, card_uuid: str) -> SimpleResponse:
        """
        Registers a maintenance intervention for the machine.

        Args:
            card_uuid (str): The UUID of the user's card.

        Returns:
            SimpleResponse: The simple response object indicating the success or failure of the operation.
        """
        try:
            self.updateMachineLastSeen()
            with MachineLogic.database.getSession() as session:
                user_repo = MachineLogic.database.getUserRepository(session)
                user = user_repo.getUserByCardUUID(card_uuid)
                if user is None:
                    return SimpleResponse(False, "Wrong user card")
                if not user.role.maintenance or user.disabled:
                    return SimpleResponse(False, "Not authorized")

                intervention_repo = MachineLogic.database.getInterventionRepository(session)
                intervention_repo.registerInterventionsDone(self._machine_id, user.user_id)

                return SimpleResponse(True, "")
        except Exception as e:
            logging.error("registerMaintenance exception %s", str(e), exc_info=True)
            return SimpleResponse(False, "BACKEND EXCEPTION")
