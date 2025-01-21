from leapp import reporting
from leapp.libraries.common.rpms import has_package
from leapp.libraries.stdlib import api
from leapp.models import DistributionSignedRPM

import subprocess

FMT_LIST_SEPARATOR = '\n    - '


class MySQLCheckLib:
    REMOVED_ARGS = [
        '--avoid-temporal-upgrade',
        '--show-old-temporals',
        '--old',
        '--new',
        '--default-authentication-plugin',
        '--no-dd-upgrade',
        '--language',
        '--ssl',
        '--admin-ssl',
        '--character-set-client-handshake',
        '--old-style-user-limits',
    ]

    # Link URL for mysql-server report
    report_server_inst_link_url = 'https://access.redhat.com/articles/7099234'

    found_arguments = set()
    found_options = set()

    def _generate_mysql_present_report(self):
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
                'complicated setups further steps might be needed.'
            )),
            reporting.Severity(self.report_severity),
            reporting.Groups([reporting.Severity.LOW]),
            reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                                   url=self.report_server_inst_link_url),
            reporting.RelatedResource('package', 'mysql-server'),
            reporting.Remediation(hint=(
                'Dump or backup your data before proceeding with the upgrade '
                'and consult attached article '
                '\'Migrating MySQL databases from RHEL 9 to RHEL 10\' '
                'with up to date recommended steps before and after the upgrade - '
                'especially different ways of backing up your data or steps you'
                'may need to take manually.'
            )),
            ])

    def _generate_deprecated_config_report(self):
        """
        Create report on mysql-server deprecated configuration.

        Apart from showing user the article for upgrade process, we inform the
        user that there are deprecated configuration options being used and
        proceeding with upgrade will result in MySQL server failing to start.
        """

        generated_list = ''
        if self.found_options:
            generated_list += (
                'Following configuration options won\'t work on a new version '
                'of MySQL after upgrading and have to be removed from config files:'
                )

            for arg in self.found_options:
                self.report_server_inst_summary += FMT_LIST_SEPARATOR + arg

            generated_list += (
                '\nDefault configuration file is present in `/etc/my.cnf`\n'
            )

        if self.found_arguments:
            generated_list += (
                'Following startup argument won\'t work on a new version '
                'of MySQL after upgrading and have to be removed from '
                'systemd service files:'
                )

            for arg in self.found_arguments:
                self.report_server_inst_summary += FMT_LIST_SEPARATOR + arg

            generated_list += (
                '\nDefault service override file is present in '
                '`/etc/systemd/system/mysqld.service.d/override.conf`'
            )

        reporting.create_report([
            reporting.Title('MySQL is using configuration that will be invalid after upgrade'),
            reporting.Summary((
                'MySQL server component will be upgraded. '
                'Since RHEL-10 includes MySQL server 8.4 by default, '
                'it is necessary to proceed with additional steps. '
                'Some options that are currently used in MySQL configuration are '
                'deprecated and will result in MySQL server failing to start '
                'after upgrading.'
                'In simple setups MySQL server should automatically upgrade all '
                'data on first start, after RHEL upgrade is completed. In more '
                'complicated setups further steps might be needed.'
            )),
            reporting.Severity(self.report_severity),
            reporting.Groups([reporting.Severity.MEDIUM]),
            reporting.ExternalLink(title='Migrating MySQL databases from RHEL 9 to RHEL 10',
                                   url=self.report_server_inst_link_url),
            reporting.RelatedResource('package', 'mysql-server'),
            reporting.Remediation(hint=(
                'To ensure smooth upgrade process it is strongly recommended to '
                'remove deprecated config options \n' +
                generated_list +
                'Dump or backup your data before proceeding with the upgrade '
                'and consult attached article '
                '\'Migrating MySQL databases from RHEL 9 to RHEL 10\' '
                'with up to date recommended steps before and after the upgrade - '
                'especially different ways of backing up your data or steps you'
                'may need to take manually.'
            )),
            ])

    def _generate_report(self):
        """
        Create report on mysql-server package installation detection.

        Should remind user about present MySQL server package
        installation, warn them about necessary additional steps, and
        redirect them to online documentation for the upgrade process.
        """

        if self.found_arguments or self.found_options:
            self._generate_deprecated_config_report()
        else:
            self._generate_mysql_present_report()

    def _check_incompatible_config(self):
        # mysqld --validate-config --log-error-verbosity=2
        # 2024-12-18T11:40:04.725073Z 0 [Warning] [MY-011069] [Server]
        # The syntax '--old' is deprecated and will be removed in a future release.
        out = subprocess.run(['mysqld', '--validate-config', '--log-error-verbosity=2'],
                             capture_output=True,
                             check=False)

        stderr = out.stderr.decode("utf-8")
        if 'deprecated' in stderr:
            self.found_options = {arg for arg
                                  in self.REMOVED_ARGS
                                  if arg in stderr}

    def _check_incompatible_launch_param(self):
        # Check /etc/systemd/system/mysqld.service.d/override.conf
        try:
            with open('/etc/systemd/system/mysqld.service.d/override.conf') as f:
                file_content = f.read()
                self.found_arguments = {arg for arg
                                        in self.REMOVED_ARGS
                                        if arg in file_content}
        except OSError:
            # File probably doesn't exist, ignore it and pass
            pass

    def report_installed_packages(self, _context=api):
        """
        Create reports according to detected MySQL packages.

        Create the report if the mysql-server rpm (RH signed) is installed.
        """

        self._check_incompatible_config()
        self._check_incompatible_launch_param()

        if has_package(DistributionSignedRPM, 'mysql-server', context=_context):
            self._generate_report()
