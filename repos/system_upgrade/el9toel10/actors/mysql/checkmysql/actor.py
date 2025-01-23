from leapp.actors import Actor
from leapp.libraries.actor import mysqlcheck
from leapp.models import MySQLConfiguration, Report
from leapp.tags import ChecksPhaseTag, IPUWorkflowTag


class MySQLCheck(Actor):
    """
    Actor checking for presence of MySQL installation.

    Provides user with information related to upgrading systems
    with MySQL installed.
    """
    name = 'mysql_check'
    consumes = (MySQLConfiguration,)
    produces = (Report,)
    tags = (ChecksPhaseTag, IPUWorkflowTag)

    def process(self) -> None:
        mysqlcheck.process()
