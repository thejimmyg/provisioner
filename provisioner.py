import os
import subprocess
import shlex
import selectors
import json
import argparse


class ExecError(OSError):
    def __init__(self, exit_code, stdout, stderr, *k, **p):
        super().__init__(*k, **p)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class CommandRunner:
    def __init__(self, logfilename, cwd: str | None = None, env: dict | None = None):
        if cwd is None:
            self.cwd: str = os.getcwd()
        else:
            self.cwd: str = cwd
        if env is None:
            self.env: dict = {}
        else:
            self.env: dict = env
        self.log_file = open(logfilename, "w")

    def __del__(self):
        self.log_file.close()

    def exec(self, cmd, cwd=None, env=None, log_name=""):
        if cwd is None:
            cwd = self.cwd
        if env is None:
            env = self.env
        self.log_file.write(
            f"{log_name}{cwd} % {' '.join([shlex.quote(term) for term in cmd])}\n"
        )
        self.log_file.flush()
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout_lines = []
        stderr_lines = []
        # Read both stdout and stderr simultaneously
        sel = selectors.DefaultSelector()
        assert process.stdout is not None
        assert process.stderr is not None
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)
        stdout_ok = True
        stderr_ok = True
        while stdout_ok or stderr_ok:
            for key, _ in sel.select():
                line = key.fileobj.readline()  #  type: ignore
                if not line:
                    if key.fileobj is process.stdout:
                        stdout_ok = False
                    else:
                        stderr_ok = False
                elif stdout_ok or stderr_ok:
                    if key.fileobj is process.stdout:
                        self.log_file.write(f"{log_name}{line}")
                        self.log_file.flush()
                        stdout_lines.append(line)
                    else:
                        self.log_file.write(f"{log_name}{line}")
                        self.log_file.flush()
                        stderr_lines.append(line)
        # Calling this closes open files
        o, e = process.communicate()
        assert o == "", o
        assert e == "", e
        exit_code = process.wait()
        if exit_code != 0:
            self.log_file.write(f"{log_name}Exit code: {exit_code}\n")
            self.log_file.flush()
        stdout = "\n".join(stdout_lines)
        stderr = "\n".join(stderr_lines)
        if exit_code != 0:
            raise ExecError(
                exit_code, stdout, stderr, f"Exec failed: {stderr or stdout}"
            )
        return stdout, stderr


class AWSCommandRunner:
    argparse_group_name = "aws"
    argparse_group_description = "Verify that the account and credentials being used match the expected values set by these flags"

    @classmethod
    def add_group(cls, group):
        group.add_argument(
            "--region", help="expected AWS region e.g. eu-west-2", required=True
        )
        group.add_argument(
            "--account",
            help="expected 12 digit AWS account number e.g. 000000000000",
            required=True,
        )
        group.add_argument(
            "--user",
            help="expected AWS user as obtained from 'aws sts get-caller-identity' e.g. AKIAIOSFODNN7EXAMPLE",
            required=True,
        )
        return group

    def __init__(
        self,
        command_runner: CommandRunner,
        region,
        account,
        user,
    ):
        self._command_runner = command_runner
        self.user: str = user
        self.account: str = account
        self.region: str = region
        if not (
            self._command_runner.env.get("AWS_DEFAULT_REGION", region)
            == self._command_runner.env.get("AWS_REGION", region)
            == region
        ):
            raise Exception(
                "The region specificed does not match the AWS_DEFAULT_REGION and AWS_REGION environment variables"
            )
        AWS_ACCESS_KEY_ID = self._command_runner.env["AWS_ACCESS_KEY_ID"]
        AWS_SECRET_ACCESS_KEY = self._command_runner.env["AWS_SECRET_ACCESS_KEY"]
        if AWS_ACCESS_KEY_ID == AWS_SECRET_ACCESS_KEY == "test":
            self.ENDPOINT_URL = "http://localhost:4566"
            self.AWS_CMD = "awslocal"
        else:
            # Can't test prodution credentials easily in a unit test, set them as the default
            self.ENDPOINT_URL = None
            self.AWS_CMD = "aws"
        stdout, stderr = self.aws(["sts", "get-caller-identity"])
        assert stderr == "", stderr
        caller = json.loads(stdout)
        if caller["Account"] != account:
            actual_account = caller["Account"]
            raise Exception(
                f"Provisioner instantiated with account '{account}' but you are actually running as account '{actual_account}'"
            )
        self.account: str = account
        if caller["UserId"] != user:
            actual_user = caller["UserId"]
            raise Exception(
                f"Provisioner instantiated with user '{user}' but you are actually running as user '{actual_user}'"
            )
        self.user: str = user

    def aws(self, cmd):
        return self._command_runner.exec(
            [self.AWS_CMD, f"--region={self.region}"] + cmd
        )


class StackProvisioner:
    argparse_group_name = "stackprovisioner"
    argparse_group_description = (
        "Settings affecting all stacks that make up this application"
    )

    @classmethod
    def add_group(cls, group):
        group.add_argument(
            "--cloudformation-bucket",
            help="S3 bucket name where templates, lambda function code and other artifacts that CloudFormation will deploy should be placed",
            required=True,
        )
        group.add_argument(
            "--stack-name-prefix",
            default="",
            help="a name to add to the start of every stack deployed by this stack provisioner e.g. My-Stack-Dev-",
        )
        group.add_argument(
            "--global-postfix",
            default="",
            help="string to add to the end of any resources which share a global AWS namespace (like S3 bucket names, Cognito domain names etc) to help make them unique e.g. -zyi3uv",
        )
        return group

    def __init__(
        self,
        aws_command_runner: AWSCommandRunner,
        cloudformation_bucket: str,
        stack_name_prefix: str = "",
        global_postfix: str = "",
        stacks: list | None = None,
    ):
        self.stacks: list = stacks or []
        self.aws_command_runner = aws_command_runner
        self.cloudformation_bucket = (
            cloudformation_bucket  # we'll leave the user to add the global_postfix
        )
        for c in stack_name_prefix:
            if not (c.isdigit() or c.islower() or c.isupper() or c in ["-", "_"]):
                raise ValueError(
                    f"Unexpected character '{c}' in stack_name_prefix, please stick to letters numbers, - and _"
                )
        self.stack_name_prefix = stack_name_prefix
        for c in global_postfix:
            if not (c.isdigit() or c.islower() or c == "-"):
                raise ValueError(
                    f"Unexpected character '{c}' in global_prefix, please stick to lowercase letters, numbers and -"
                )
        self.global_postfix = global_postfix
        self.ensure_versioned_bucket_exists_and_create_if_not(
            self.cloudformation_bucket + global_postfix
        )
        self.start_stack_status = self.describe_stacks(
            [stack_name + self.global_postfix for stack_name in self.stacks]
        )

    def describe_stacks(self, stack_names):
        return None
        # cmd = [
        #     "cloudformation",
        #     "describe-stacks",
        # ]
        # for stack_name in stack_names:
        #     cmd += [
        #         "--stack-name",
        #         stack_name,
        #     ]
        # stdout, _ = self.aws_command_runner.aws(cmd)
        # res = json.loads(stdout)
        # print(stack_names, res)
        # return res

    def ensure_versioned_bucket_exists_and_create_if_not(self, bucket):
        try:
            stdout, _ = self.aws_command_runner.aws(
                ["s3api", "get-bucket-versioning", "--bucket", bucket]
            )
            if stdout.strip() and json.loads(stdout)["Status"] == "Enabled":
                print(
                    "The bucket already exists, but bucket versioning is enabled, so we can continue."
                )
            else:
                print(stdout)
                raise Exception(
                    f"The bucket '{bucket}' already exists, but versioning is not enabled"
                )
        except ExecError:
            # Assume the bucket does not exist
            self.aws_command_runner.aws(
                [
                    "s3api",
                    "create-bucket",
                    "--bucket",
                    bucket,
                    "--create-bucket-configuration",
                    f"LocationConstraint={self.aws_command_runner.region}",
                ]
            )
            self.aws_command_runner.aws(
                [
                    "s3api",
                    "put-bucket-versioning",
                    "--bucket",
                    bucket,
                    "--versioning-configuration",
                    "Status=Enabled",
                ]
            )
            print("Created the bucket and enabled versioning.")


def parse_args(parser, group_classes, args):
    for GroupClass in group_classes:
        group = parser.add_argument_group(
            GroupClass.argparse_group_name,
            GroupClass.argparse_group_description,
        )
        GroupClass.add_group(group)

    args = parser.parse_args(args)

    arg_groups = {}
    for group in parser._action_groups:
        group_dict = {
            action.dest: getattr(args, action.dest, None)
            for action in group._group_actions
        }
        arg_groups[group.title] = group_dict
    return arg_groups
