#!/usr/bin/python3
""" Implementation of the console frontend of the Todoist backup utility """

import argparse
from pathlib import Path
from .virtual_fs import ZipVirtualFs

class ConsoleFrontend:
    """ Implementation of the console frontend for the Todoist backup tool """
    def __init__(self, controller_factory, controller_dependencies_factory):
        self.__controller_factory = controller_factory
        self.__controller_dependencies_factory = controller_dependencies_factory
        self.__controller = None

    @staticmethod
    def __add_authorization_group(parser):
        token_group = parser.add_mutually_exclusive_group(required=True)
        token_group.add_argument("--token", type=str,
                                 help="todoist API token (see Settings --> Integration)")
        token_group.add_argument("--token-file", type=str,
                                 help="file containing the todoist API token")
        parser.add_argument("--email", type=str,
                            help="todoist email address for authorization")
        parser.add_argument("--password", type=str,
                            help="todoist email address for authorization")

    def __parse_command_line_args(self, prog, arguments):
        example1_str = "Example: {} download --token 0123456789abcdef --email myemail@example.com --password P4ssW0rD".format(prog)
        parser = argparse.ArgumentParser(prog=prog, formatter_class=argparse.RawTextHelpFormatter,
                                         epilog=example1_str)
        parser.add_argument("--verbose", action="store_true", help="print details to console")
        subparsers = parser.add_subparsers(dest='action')
        subparsers.required = True

        # create the parser for the "download" command
        parser_download = subparsers.add_parser('download', help='download specified backup')
        parser_download.set_defaults(func=self.handle_download)
        parser_download.add_argument("--with-attachments", action="store_true",
                                     help="download attachments and attach to the backup file")
        parser_download.add_argument("--output-file", type=str,
                                     help="name of the file that will store the backup")
        self.__add_authorization_group(parser_download)

        return parser.parse_args(arguments)

    def run(self, prog, arguments):
        """ Runs the Todoist backup tool frontend with the specified command line arguments """
        args = self.__parse_command_line_args(prog, arguments)
        args.func(args)

    @staticmethod
    def __get_auth(args):
        token = Path(args.token_file).read_text() if args.token_file else args.token
        email = args.email
        password = args.password
        return {"token": token, "email": email, "password": password}

    def handle_download(self, args):
        """ Handles the download subparser with the specified command line arguments """

        # Configure controller
        auth = self.__get_auth(args)
        dependencies = self.__controller_dependencies_factory(auth, args.verbose)
        controller = self.__controller_factory(dependencies)

        # Setup zip virtual fs
        with ZipVirtualFs(args.output_file) as zipvfs:
            # Execute requested action
            controller.download(zipvfs, with_attachments=args.with_attachments)