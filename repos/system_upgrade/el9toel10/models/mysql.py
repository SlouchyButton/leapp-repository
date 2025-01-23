from leapp.models import fields, Model
from leapp.topics import SystemInfoTopic


class MySQLConfiguration(Model):
    """
    Model describing current state of MySQL server including configuration compatibility
    """

    topic = SystemInfoTopic

    mysql_present = fields.Boolean(default=False)

    """
    Configured options which are removed in RHEL 10 MySQL
    """
    removed_options = fields.List(fields.String(), default=[])
    removed_arguments = fields.List(fields.String(), default=[])
