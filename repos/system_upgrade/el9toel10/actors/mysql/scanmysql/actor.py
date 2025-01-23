from leapp.actors import Actor
from leapp.libraries.actor import scanmysql
from leapp.models import DistributionSignedRPM, MySQLConfiguration
from leapp.tags import FactsPhaseTag, IPUWorkflowTag


class ScanMySQL(Actor):
    """
    Actor checking for presence of MySQL installation.

    Provides user with information related to upgrading systems
    with MySQL installed.
    """
    name = 'scan_mysql'
    consumes = (DistributionSignedRPM,)
    produces = (MySQLConfiguration,)
    tags = (FactsPhaseTag, IPUWorkflowTag)

    def process(self) -> None:
        self.produce(scanmysql.check_status())
