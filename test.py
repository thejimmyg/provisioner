import os
import json
from unittest import TestCase
from unittest.mock import Mock
from provisioner import (
    CommandRunner,
    ExecError,
    AWSCommandRunner,
    StackProvisioner,
    ExecError,
    parse_args,
)
import argparse

# Just to give the text output from help a knowable width
os.environ["COLUMNS"] = "122"


path = os.environ["PATH"]
logfilename = "test.log"


class TestCommandRunner(TestCase):
    def test_create_command_runner(self):
        command_runner = CommandRunner(logfilename=logfilename, cwd=None, env=None)
        self.assertEqual(os.getcwd(), command_runner.cwd)
        self.assertDictEqual({}, command_runner.env)

    def test_create_command_runner_with_cwd_and_env(self):
        command_runner = CommandRunner(
            logfilename=logfilename, cwd="/some/path", env=dict(one="1")
        )
        self.assertEqual("/some/path", command_runner.cwd)
        self.assertDictEqual({"one": "1"}, command_runner.env)

    def test_command_runner_logfile_is_closed(self):
        command_runner = CommandRunner(logfilename=logfilename, cwd=None, env=None)
        openlogfile = command_runner.log_file
        del command_runner
        self.assertTrue(openlogfile.closed)

    def test_run_a_comamnd_and_check_stdout_logs(self):
        command_runner = CommandRunner(
            logfilename=logfilename, cwd=None, env=dict(PATH=path)
        )
        stdout, stderr = command_runner.exec(["echo", "hello"])
        self.assertEqual(stdout, "hello\n")
        self.assertEqual(stderr, "")
        with open(logfilename, "r") as fp:
            self.assertEqual(
                f"""{os.getcwd()} % echo hello
hello
""",
                fp.read(),
            )

    def test_run_a_comamnd_and_check_stderr_logs(self):
        command_runner = CommandRunner(
            logfilename=logfilename, cwd=None, env=dict(PATH=path)
        )
        stdout, stderr = command_runner.exec(
            ["sh", "-c", "echo 'hello1' 1>&2 && echo 'hello2' && echo 'hello3' 1>&2"]
        )
        self.assertEqual(stdout, "hello2\n")
        self.assertEqual(stderr, "hello1\n\nhello3\n")
        with open(logfilename, "r") as fp:
            self.assertEqual(
                f"""{os.getcwd()} % sh -c 'echo '"'"'hello1'"'"' 1>&2 && echo '"'"'hello2'"'"' && echo '"'"'hello3'"'"' 1>&2'
hello1
hello2
hello3
""",
                fp.read(),
            )

    def test_run_a_failing_comamnd_and_check_logs(self):
        command_runner = CommandRunner(
            logfilename=logfilename, cwd=None, env=dict(PATH=path)
        )
        with self.assertRaises(ExecError) as cm:
            command_runner.exec(["sh", "-c", 'echo "out" && echo "err" 1>&2 && exit 1'])
        self.assertEqual(cm.exception.exit_code, 1)
        self.assertEqual(cm.exception.stdout, "out\n")
        self.assertEqual(cm.exception.stderr, "err\n")
        with open(logfilename, "r") as fp:
            self.assertEqual(
                f"""{os.getcwd()} % sh -c 'echo "out" && echo "err" 1>&2 && exit 1'
out
err
Exit code: 1
""",
                fp.read(),
            )

    def test_cwd_and_env_work_globally(self):
        command_runner = CommandRunner(
            logfilename=logfilename, cwd="/", env=dict(CUSTOM_ENV="custom_env")
        )
        stdout, stderr = command_runner.exec(["sh", "-c", 'echo "$CUSTOM_ENV $PWD"'])
        self.assertEqual("custom_env /\n", stdout)
        self.assertEqual("", stderr)

        with open(logfilename, "r") as fp:
            self.assertEqual(
                f"""/ % sh -c 'echo "$CUSTOM_ENV $PWD"'
custom_env /
""",
                fp.read(),
            )

    def test_cwd_and_env_work_locally(self):
        command_runner = CommandRunner(
            logfilename=logfilename,
            cwd="/does/not/exist",
            env=dict(CUSTOM_ENV="custom_env"),
        )
        stdout, stderr = command_runner.exec(
            ["sh", "-c", 'echo "$CUSTOM_ENV $PWD"'],
            cwd="/",
            env=dict(CUSTOM_ENV="local_custom_env"),
        )
        self.assertEqual("local_custom_env /\n", stdout)
        self.assertEqual("", stderr)
        with open(logfilename, "r") as fp:
            self.assertEqual(
                f"""/ % sh -c 'echo "$CUSTOM_ENV $PWD"'
local_custom_env /
""",
                fp.read(),
            )

    def test_custom_log_name(self):
        command_runner = CommandRunner(
            logfilename=logfilename, cwd=None, env=dict(PATH=path)
        )
        with self.assertRaises(ExecError) as cm:
            command_runner.exec(
                ["sh", "-c", 'echo "out" && echo "err" 1>&2 && exit 1'],
                log_name="[custom] ",
            )
        self.assertEqual(cm.exception.exit_code, 1)
        self.assertEqual(cm.exception.stdout, "out\n")
        self.assertEqual(cm.exception.stderr, "err\n")
        with open(logfilename, "r") as fp:
            self.assertEqual(
                f"""[custom] {os.getcwd()} % sh -c 'echo "out" && echo "err" 1>&2 && exit 1'
[custom] out
[custom] err
[custom] Exit code: 1
""",
                fp.read(),
            )


localenv = dict(
    AWS_REGION="eu-west-2",
    AWS_ACCESS_KEY_ID="test",
    AWS_SECRET_ACCESS_KEY="test",
    PATH=path,
)


class TestAWSCommandRunner(TestCase):
    def test_args(self):
        parser = argparse.ArgumentParser()
        group2 = parser.add_argument_group("group2")
        group2.add_argument("--test2", help="test2")
        arg_groups = parse_args(
            parser,
            [AWSCommandRunner],
            "--region eu-west-2 --account 00000000000 --user AKIAIOSFODNN7EXAMPLE".split(),
        )
        self.assertDictEqual(
            arg_groups,
            {
                "aws": dict(
                    region="eu-west-2",
                    account="00000000000",
                    user="AKIAIOSFODNN7EXAMPLE",
                ),
                "group2": dict(test2=None),
                "options": dict(help=None),
                "positional arguments": dict(),
            },
        )
        # self.maxDiff = None
        # parser.print_help()
        self.assertEqual(
            """usage: python3 -m unittest [-h] [--test2 TEST2] --region REGION --account ACCOUNT --user USER

options:
  -h, --help         show this help message and exit

group2:
  --test2 TEST2      test2

aws:
  Verify that the account and credentials being used match the expected values set by these flags

  --region REGION    expected AWS region e.g. eu-west-2
  --account ACCOUNT  expected 12 digit AWS account number e.g. 000000000000
  --user USER        expected AWS user as obtained from 'aws sts get-caller-identity' e.g. AKIAIOSFODNN7EXAMPLE
""",
            parser.format_help(),
        )

    def test_create_aws_command_runner_prod_env(self):
        prodenv = dict(
            AWS_REGION="eu-west-2",
            AWS_ACCESS_KEY_ID="PRODID",
            AWS_SECRET_ACCESS_KEY="SECRET",
            PATH=path,
        )
        command_runner = CommandRunner(logfilename=logfilename, env=prodenv)
        exec_method = Mock()

        def side_effect(cmd, cwd=None, env=None):
            self.assertEqual(
                ["aws", "--region=eu-west-2", "sts", "get-caller-identity"], cmd
            )
            return (
                json.dumps(
                    {
                        "UserId": "AKIAIOSFODNN7EXAMPLE",
                        "Account": "000000000000",
                        "Arn": "arn:aws:iam::000000000000:root",
                    }
                ),
                "",
            )

        exec_method.side_effect = side_effect
        command_runner.exec = exec_method
        aws_command_runner = AWSCommandRunner(
            region="eu-west-2",
            user="AKIAIOSFODNN7EXAMPLE",
            account="000000000000",
            command_runner=command_runner,
        )
        exec_method.assert_called_once()
        self.assertEqual(aws_command_runner.region, "eu-west-2")
        self.assertEqual(aws_command_runner.user, "AKIAIOSFODNN7EXAMPLE")
        self.assertEqual(aws_command_runner.account, "000000000000")
        self.assertEqual(aws_command_runner.ENDPOINT_URL, None)
        self.assertEqual(aws_command_runner.AWS_CMD, "aws")

    def test_create_aws_command_runner_invalid_account(self):
        command_runner = CommandRunner(logfilename=logfilename, env=localenv)
        exec_method = Mock()

        def side_effect(cmd, cwd=None, env=None):
            self.assertEqual(
                ["awslocal", "--region=eu-west-2", "sts", "get-caller-identity"], cmd
            )
            return (
                json.dumps(
                    {
                        "UserId": "AKIAIOSFODNN7EXAMPLE",
                        "Account": "000000000000",
                        "Arn": "arn:aws:iam::111:root",
                    }
                ),
                "",
            )

        exec_method.side_effect = side_effect
        command_runner.exec = exec_method
        with self.assertRaises(Exception) as cm:
            AWSCommandRunner(
                region="eu-west-2",
                user="AKIAIOSFODNN7EXAMPLE",
                account="111",
                command_runner=command_runner,
            )
        exec_method.assert_called_once()
        self.assertEqual(
            "Provisioner instantiated with account '111' but you are actually running as account '000000000000'",
            str(cm.exception),
        )

    def test_create_command_runner_aws_invalid_user(self):
        command_runner = CommandRunner(logfilename=logfilename, env=localenv)
        exec_method = Mock()

        def side_effect(cmd, cwd=None, env=None):
            self.assertEqual(
                ["awslocal", "--region=eu-west-2", "sts", "get-caller-identity"], cmd
            )
            return (
                json.dumps(
                    {
                        "UserId": "AKIAIOSFODNN7EXAMPLE",
                        "Account": "000000000000",
                        "Arn": "arn:aws:iam::111:root",
                    }
                ),
                "",
            )

        exec_method.side_effect = side_effect
        command_runner.exec = exec_method
        with self.assertRaises(Exception) as cm:
            AWSCommandRunner(
                region="eu-west-2",
                user="AKIAIOSFODNN7WRONG",
                account="000000000000",
                command_runner=command_runner,
            )
        exec_method.assert_called_once()
        self.assertEqual(
            "Provisioner instantiated with user 'AKIAIOSFODNN7WRONG' but you are actually running as user 'AKIAIOSFODNN7EXAMPLE'",
            str(cm.exception),
        )

    def test_create_aws_command_runner_invalid_region(self):
        with self.assertRaises(Exception) as cm:
            AWSCommandRunner(
                region="us-east-1",  # Different region from localenv above
                user="AKIAIOSFODNN7EXAMPLE",
                account="000000000000",
                command_runner=CommandRunner(logfilename=logfilename, env=localenv),
            )
        self.assertEqual(
            "The region specificed does not match the AWS_DEFAULT_REGION and AWS_REGION environment variables",
            str(cm.exception),
        )


class TestEnsureVersionedBucket(TestCase):
    def get_local_aws_command_runner(self):
        command_runner = CommandRunner(logfilename=logfilename, env=localenv)
        exec_method = Mock()

        def side_effect(cmd, cwd=None, env=None):
            self.assertEqual(
                ["awslocal", "--region=eu-west-2", "sts", "get-caller-identity"], cmd
            )
            return (
                json.dumps(
                    {
                        "UserId": "AKIAIOSFODNN7EXAMPLE",
                        "Account": "000000000000",
                        "Arn": "arn:aws:iam::000000000000:root",
                    }
                ),
                "",
            )

        exec_method.side_effect = side_effect

        real_exec = command_runner.exec
        command_runner.exec = exec_method
        aws_command_runner = AWSCommandRunner(
            region="eu-west-2",
            user="AKIAIOSFODNN7EXAMPLE",
            account="000000000000",
            command_runner=command_runner,
        )
        exec_method.assert_called_once()
        command_runner.exec = real_exec
        return aws_command_runner

    def get_local_stack_provisioner(
        self, bucket_status="versioned", global_postfix="", **p
    ):
        aws_method = Mock()

        def side_effect(cmd):
            assert bucket_status in ["versioned", "not_existing", "not_versioned"]
            if bucket_status == "versioned":
                assert aws_method.call_count == 1, aws_method.call_count
                self.assertEqual(
                    [
                        "s3api",
                        "get-bucket-versioning",
                        "--bucket",
                        "testbucket" + global_postfix,
                    ],
                    cmd,
                )
                return (
                    json.dumps(
                        {
                            "Status": "Enabled",
                        }
                    ),
                    "",
                )
            elif bucket_status == "not_versioned":
                assert aws_method.call_count == 1, aws_method.call_count
                self.assertEqual(
                    [
                        "s3api",
                        "get-bucket-versioning",
                        "--bucket",
                        "testbucket" + global_postfix,
                    ],
                    cmd,
                )
                return (
                    "",
                    "",
                )
            elif bucket_status == "not_existing":
                assert (
                    aws_method.call_count >= 1 and aws_method.call_count <= 4
                ), aws_method.call_count
                if aws_method.call_count == 1:
                    self.assertEqual(
                        [
                            "s3api",
                            "get-bucket-versioning",
                            "--bucket",
                            "testbucket" + global_postfix,
                        ],
                        cmd,
                    )
                    raise ExecError(
                        "Pretending the get bucket versioning command failed",
                        "example stdout",
                        "example stderr",
                        255,
                    )
                elif aws_method.call_count == 2:
                    self.assertEqual(
                        [
                            "s3api",
                            "create-bucket",
                            "--bucket",
                            "testbucket" + global_postfix,
                            "--create-bucket-configuration",
                            f"LocationConstraint=eu-west-2",
                        ],
                        cmd,
                    )
                    return (
                        "",
                        "",
                    )
                elif aws_method.call_count == 3:
                    self.assertEqual(
                        [
                            "s3api",
                            "put-bucket-versioning",
                            "--bucket",
                            "testbucket" + global_postfix,
                            "--versioning-configuration",
                            "Status=Enabled",
                        ],
                        cmd,
                    )
                    return (
                        "",
                        "",
                    )

        aws_command_runner = self.get_local_aws_command_runner()
        real_aws = aws_command_runner.aws
        aws_method.side_effect = side_effect
        aws_command_runner.aws = aws_method
        sp = StackProvisioner(aws_command_runner, global_postfix=global_postfix, **p)
        if bucket_status == "not_existing":
            self.assertEqual(3, aws_method.call_count)
        else:
            self.assertEqual(1, aws_method.call_count)
        aws_command_runner.aws = real_aws
        return sp

    def test_stack_provisioner_init(self):
        sp = self.get_local_stack_provisioner(cloudformation_bucket="testbucket")

        self.assertEqual("testbucket", sp.cloudformation_bucket)
        self.assertEqual("", sp.stack_name_prefix)
        self.assertEqual("", sp.global_postfix)

        sp = self.get_local_stack_provisioner(
            cloudformation_bucket="testbucket",
            stack_name_prefix="123",
            global_postfix="789",
        )
        self.assertEqual("testbucket", sp.cloudformation_bucket)
        self.assertEqual("789", sp.global_postfix)
        self.assertEqual("123", sp.stack_name_prefix)

        with self.assertRaises(Exception) as cm:
            sp = self.get_local_stack_provisioner(
                cloudformation_bucket="testbucket", bucket_status="not_versioned"
            )
        self.assertEqual(
            "The bucket 'testbucket' already exists, but versioning is not enabled",
            str(cm.exception),
        )

        sp = self.get_local_stack_provisioner(
            cloudformation_bucket="testbucket", bucket_status="not_existing"
        )
        self.assertEqual("testbucket", sp.cloudformation_bucket)
        self.assertEqual("", sp.stack_name_prefix)
        self.assertEqual("", sp.global_postfix)

    def test_stack_provisioner_invalid_init(self):
        with self.assertRaises(ValueError) as cm:
            self.get_local_stack_provisioner(
                cloudformation_bucket="testbucket", stack_name_prefix="1+23"
            )
        self.assertEqual(
            "Unexpected character '+' in stack_name_prefix, please stick to letters numbers, - and _",
            str(cm.exception),
        )
        with self.assertRaises(ValueError) as cm:
            self.get_local_stack_provisioner(
                cloudformation_bucket="testbucket", global_postfix="7+89"
            )
        self.assertEqual(
            "Unexpected character '+' in global_prefix, please stick to lowercase letters, numbers and -",
            str(cm.exception),
        )

    def test_args(self):
        parser = argparse.ArgumentParser()
        group2 = parser.add_argument_group("group2")
        group2.add_argument("--test2", help="test2")
        arg_groups = parse_args(
            parser,
            [StackProvisioner],
            "--cloudformation-bucket testbucket --stack-name-prefix MyStack- --global-postfix -123".split(),
        )

        self.assertDictEqual(
            arg_groups,
            {
                "stackprovisioner": dict(
                    cloudformation_bucket="testbucket",
                    stack_name_prefix="MyStack-",
                    global_postfix="-123",
                ),
                "group2": dict(test2=None),
                "options": dict(help=None),
                "positional arguments": dict(),
            },
        )
        # self.maxDiff = None
        # parser.print_help()
        self.assertEqual(
            """usage: python3 -m unittest [-h] [--test2 TEST2] --cloudformation-bucket CLOUDFORMATION_BUCKET
                           [--stack-name-prefix STACK_NAME_PREFIX] [--global-postfix GLOBAL_POSTFIX]

options:
  -h, --help            show this help message and exit

group2:
  --test2 TEST2         test2

stackprovisioner:
  Settings affecting all stacks that make up this application

  --cloudformation-bucket CLOUDFORMATION_BUCKET
                        S3 bucket name where templates, lambda function code and other artifacts that CloudFormation
                        will deploy should be placed
  --stack-name-prefix STACK_NAME_PREFIX
                        a name to add to the start of every stack deployed by this stack provisioner e.g. My-Stack-Dev-
  --global-postfix GLOBAL_POSTFIX
                        string to add to the end of any resources which share a global AWS namespace (like S3 bucket
                        names, Cognito domain names etc) to help make them unique e.g. -zyi3uv
""",
            parser.format_help(),
        )
