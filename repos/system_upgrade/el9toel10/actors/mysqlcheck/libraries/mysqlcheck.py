from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

import subprocess

FMT_LIST_SEPARATOR = '\n    - '

# https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html
# https://dev.mysql.com/doc/refman/8.0/en/server-options.html
# https://dev.mysql.com/doc/refman/8.4/en/mysql-nutshell.html
REMOVED_ARGS = [
    '--avoid-temporal-upgrade',
    'avoid_temporal_upgrade',
    '--show-old-temporals',
    'show_old_temporals',
    '--old',
    '--new',
    '--default-authentication-plugin',
    'default_authentication_plugin',
    '--no-dd-upgrade',
    '--language',
    '--ssl',
    '--admin-ssl',
    '--character-set-client-handshake',
    '--old-style-user-limits',
]

# Link URL for mysql-server report
report_server_inst_link_url = 'https://access.redhat.com/articles/7099234'


def _generate_mysql_present_report():
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.

    This report is used in case MySQL package is detected, but no
    immediate action is needed.
    """
    reporting.create_report([
        reporting.Title('Further action to upgrade MySQL might be needed'),
        reporting.Summary((
            'MySQL server component will be upgraded. '
            'Since RHEL-10 includes MySQL server 8.4 by default, '
            'it might be necessary to proceed with additional steps after '
            'RHEL upgrade is completed. In simple setups MySQL server should '
            'automatically upgrade all data on first start, but in more '
            'complicated setups manual intervention might be needed.'
        )),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                               url=report_server_inst_link_url),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.Remediation(hint=(
            'Dump or backup your data before proceeding with the upgrade '
            'and consult attached article '
            '\'Migrating MySQL databases from RHEL 9 to RHEL 10\' '
            'with up to date recommended steps before and after the upgrade.'
        )),
        ])


def _generate_deprecated_config_report(found_options, found_arguments):
    """
    Create report on mysql-server deprecated configuration.

    Apart from showing user the article for upgrade process, we inform the
    user that there are deprecated configuration options being used and
    proceeding with upgrade will result in MySQL server failing to start.
    """

    generated_list = ''
    if found_options:
        generated_list += (
            'Following configuration options won\'t work on a new version '
            'of MySQL after upgrading and have to be removed from configuration files:'
            )

        for arg in found_options:
            generated_list += FMT_LIST_SEPARATOR + arg

        generated_list += (
            '\nDefault configuration file is present at `/etc/my.cnf`\n'
        )

    if found_arguments:
        generated_list += (
            'Following startup arguments won\'t work on a new version '
            'of MySQL after upgrading and have to be removed from '
            'systemd service files:'
            )

        for arg in found_arguments:
            generated_list += FMT_LIST_SEPARATOR + arg

        generated_list += (
            '\nDefault service override file is present at '
            '`/etc/systemd/system/mysqld.service.d/override.conf`\n'
        )

    reporting.create_report([
        reporting.Title('MySQL is using configuration that will be invalid after upgrade'),
        reporting.Summary((
            'MySQL server component will be upgraded. '
            'Since RHEL-10 includes MySQL server 8.4 by default, '
            'it is necessary to proceed with additional steps. '
            'Some options that are currently used in MySQL configuration are '
            'deprecated and will result in MySQL server failing to start '
            'after upgrading. '
            'After RHEL upgrade is completed MySQL server should automatically upgrade all '
            'data on first start in simple setups. In more '
            'complicated setups manual intervention might be needed.'
        )),
        reporting.Severity(reporting.Severity.MEDIUM),
        reporting.Groups([reporting.Groups.SERVICES]),
        reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                               url=report_server_inst_link_url),
        reporting.RelatedResource('package', 'mysql-server'),
        reporting.Remediation(hint=(
            'To ensure smooth upgrade process it is strongly recommended to '
            'remove deprecated config options \n' +
            generated_list +
            'Dump or backup your data before proceeding with the upgrade '
            'and consult attached article '
            '\'Migrating MySQL databases from RHEL 9 to RHEL 10\' '
            'with up to date recommended steps before and after the upgrade.'
        )),
        ])


def _generate_report(found_options, found_arguments):
    """
    Create report on mysql-server package installation detection.

    Should remind user about present MySQL server package
    installation, warn them about necessary additional steps, and
    redirect them to online documentation for the upgrade process.
    """

    if found_arguments or found_options:
        _generate_deprecated_config_report(found_options, found_arguments)
    else:
        _generate_mysql_present_report()


def _check_incompatible_config():
    """
    Get incompatible configuration options. Since MySQL can have basically
    unlimited number of config files that can link to one another, most
    convenient way is running `mysqld` command with `--validate-config 
    --log-error-verbosity=2` arguments. Validate config only validates the
    config, without starting the MySQL server. Verbosity=2 is required to show
    deprecated options - which are removed after upgrade.

    Example output:
    2024-12-18T11:40:04.725073Z 0 [Warning] [MY-011069] [Server]
    The syntax '--old' is deprecated and will be removed in a future release.
    """
    # mysqld --validate-config --log-error-verbosity=2
    # 2024-12-18T11:40:04.725073Z 0 [Warning] [MY-011069] [Server]
    # The syntax '--old' is deprecated and will be removed in a future release.

    found_options = set()
    out = subprocess.run(['mysqld', '--validate-config', '--log-error-verbosity=2'],
                         capture_output=True,
                         check=False)

    stderr = out.stderr.decode("utf-8")
    if 'deprecated' in stderr:
        found_options = {arg for arg
                         in REMOVED_ARGS
                         if arg in stderr}
    return found_options


def _check_incompatible_launch_param():
    """
    Get incompatible launch parameters from systemd service override file
    located at /etc/systemd/system/mysqld.service.d/override.conf
    """

    found_arguments = set()
    try:
        with open('/etc/systemd/system/mysqld.service.d/override.conf') as f:
            file_content = f.read()
            found_arguments = {arg for arg
                               in REMOVED_ARGS
                               if arg in file_content}
    except OSError:
        # File probably doesn't exist, ignore it and pass
        pass

    return found_arguments


def report_installed_packages(_context=api):
    """
    Create reports according to detected MySQL packages.

    Create the report if the mysql-server rpm (RH signed) is installed.
    """

    if has_package(DistributionSignedRPM, 'mysql-server', context=_context):
        found_options = _check_incompatible_config()
        found_arguments = _check_incompatible_launch_param()
        _generate_report(found_options, found_arguments)
