import os
from unittest import TestCase
from provisioner import CommandRunner, ExecError, AWSCommandRunner, StackProvisioner
from unittest.mock import Mock

path = os.environ["PATH"]
localenv = dict(
    AWS_REGION="eu-west-2",
    AWS_ACCESS_KEY_ID="test",
    AWS_SECRET_ACCESS_KEY="test",
    PATH=path,
)
logfilename = "localstack.log"


class TestAWSCommandRunnerUserAndAccount(TestCase):
    command_runner: CommandRunner | None = None

    @classmethod
    def setUpClass(cls):
        cwd = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
        print("Running in", cwd)
        env = dict(
            DISABLE_EVENTS="1",  # This disables the callback to analytics.localstack.cloud
            PATH=os.environ["PATH"],
        )
        cls.command_runner = CommandRunner(logfilename=logfilename, cwd=cwd, env=env)
        try:
            cls.command_runner.exec(
                ["localstack", "stop"],
            )
        except ExecError:
            print(
                "Could not stop localstack, assuming it is not running ... Continuing."
            )
        print("Starting localstack ...")
        cls.command_runner.exec(
            ["localstack", "start", "-d"],
            cwd=cwd,
            env=dict(
                DEBUG="1",
                DISABLE_EVENTS="1",  # This disables the callback to analytics.localstack.cloud
                DISABLE_CORS_CHECKS="1",
                DISABLE_CUSTOM_CORS_APIGATEWAY="1",
                PATH=os.environ["PATH"],
            ),
        )
        print("done.")

    @classmethod
    def tearDownClass(cls):
        assert cls.command_runner is not None
        print("Stopping localstack ...")
        cls.command_runner.exec(
            ["localstack", "stop"],
        )
        print("done.")

    def test_create_aws_command_runner_local_env(self):
        aws_command_runner = AWSCommandRunner(
            region="eu-west-2",
            user="AKIAIOSFODNN7EXAMPLE",
            account="000000000000",
            command_runner=CommandRunner(logfilename=logfilename, env=localenv),
        )
        self.assertEqual(aws_command_runner.region, "eu-west-2")
        self.assertEqual(aws_command_runner.user, "AKIAIOSFODNN7EXAMPLE")
        self.assertEqual(aws_command_runner.account, "000000000000")
        self.assertEqual(aws_command_runner.ENDPOINT_URL, "http://localhost:4566")
        self.assertEqual(aws_command_runner.AWS_CMD, "awslocal")

    def test_create_aws_command_runner_invalid_account(self):
        command_runner = CommandRunner(logfilename=logfilename, env=localenv)
        with self.assertRaises(Exception) as cm:
            AWSCommandRunner(
                region="eu-west-2",
                user="AKIAIOSFODNN7EXAMPLE",
                account="111111111111",
                command_runner=command_runner,
            )
        self.assertEqual(
            "Provisioner instantiated with account '111111111111' but you are actually running as account '000000000000'",
            str(cm.exception),
        )

    def test_create_command_runner_aws_invalid_user(self):
        command_runner = CommandRunner(logfilename=logfilename, env=localenv)
        with self.assertRaises(Exception) as cm:
            AWSCommandRunner(
                region="eu-west-2",
                user="AKIAIOSFODNN7WRONG",
                account="000000000000",
                command_runner=command_runner,
            )
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

    def test_stack_provisioner_buckets(self):
        aws_command_runner = AWSCommandRunner(
            CommandRunner(logfilename=logfilename, env=localenv),
            region="eu-west-2",
            user="AKIAIOSFODNN7EXAMPLE",
            account="000000000000",
        )

        # Should create the bucket
        StackProvisioner(
            aws_command_runner,
            cloudformation_bucket="testbucket",
            stack_name_prefix="MyStack-",
            global_postfix="-123",
        )

        # Should be happy with the versioned bucket
        StackProvisioner(
            aws_command_runner,
            cloudformation_bucket="testbucket",
            stack_name_prefix="MyStack-",
            global_postfix="-123",
        )

    def test_stack_provisioner_buckets_fail(self):
        aws_command_runner = AWSCommandRunner(
            CommandRunner(logfilename=logfilename, env=localenv),
            region="eu-west-2",
            user="AKIAIOSFODNN7EXAMPLE",
            account="000000000000",
        )
        aws_command_runner.aws(
            [
                "s3api",
                "create-bucket",
                "--bucket",
                "unversionedtestbucket-123",
                "--create-bucket-configuration",
                f"LocationConstraint={aws_command_runner.region}",
            ]
        )
        with self.assertRaises(Exception) as cm:
            # Should not be happy with the versioned bucket
            StackProvisioner(
                aws_command_runner,
                cloudformation_bucket="unversionedtestbucket",
                stack_name_prefix="MyStack-",
                global_postfix="-123",
            )
        self.assertEqual(
            "The bucket 'unversionedtestbucket-123' already exists, but versioning is not enabled",
            str(cm.exception),
        )
