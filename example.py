import os
import sys

from provisioner import CommandRunner, AWSCommandRunner, StackProvisioner, parse_args


class OIDC:
    argparse_group_name = "oidc"
    argparse_group_description = "Settings for authorising a user via OIDC"

    @classmethod
    def add_group(cls, group):
        group.add_argument(
            "--issuer",
            help="the issuer for the JWT Authorizer",
            required=True,
        )
        group.add_argument(
            "--audience",
            help="the audience for the JWT Authorizer",
            required=True,
        )
        group.add_argument(
            "--oauth-token-url",
            help="the OAuth 2.0 token endpoint",
            required=True,
        )
        group.add_argument(
            "--oauth-authorize-url",
            help="the OAuth 2.0 authorize endpoint",
            required=True,
        )
        return group


class Frontend:
    argparse_group_name = "frontend"
    argparse_group_description = "Frontend SPA settings"

    @classmethod
    def add_group(cls, group):
        group.add_argument(
            "--frontend-bucket",
            help="S3 bucket name for publicly served front-end assets like app.css and app.js",
            required=True,
        )
        return group


class Publisher:
    argparse_group_name = "publisher"
    argparse_group_description = (
        "Settings affecting all stacks that make up this application"
    )

    @classmethod
    def add_group(cls, group):
        group.add_argument(
            "--company-two-api-url",
            help="The URL of the company/two API endpoint",
            required=True,
        )
        group.add_argument(
            "--company-one-api-url",
            help="The URL of the company/one API endpoint",
            required=True,
        )
        return group


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser()
    arg_groups = parse_args(
        parser,
        [
            AWSCommandRunner,
            StackProvisioner,
            OIDC,
            Frontend,
            Publisher,
        ],
        sys.argv[1:],
    )
    pprint.pprint(arg_groups)
    command_runner = CommandRunner('example.log', env=os.environ.copy())
    aws_command_runner = AWSCommandRunner(command_runner, **arg_groups['aws'])
    stack_provisioner = StackProvisioner(aws_command_runner, **arg_groups['stackprovisioner'])
