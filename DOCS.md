
CommandRunner(logfile, env, cwd)
 - exec()

AWSCommandRunner(command_runner, region, user, account)
 - aws()

StackProvisioner(aws_command_runner)
 - ensure_versioned_artifact_bucket_exists(bucket_name)
 - package_upload_deploy_wait(stack...)
 - stack_info(stack_name) -> {status, parameters, outputs}

Stack()
 - arg_prefix
 - @classmethod nested_parser_args(parser) -> parser

def provision(command_args, aws_command_args, stack_provisioner_args, stack1_args, ...):
  sp = StackProvisioner()
  
def cmd():
  stacks = [Stack1, Stack2, ...]
  parser = Parser()
  [Stack.parser_args(parser) for parser in stacks]
  args = parser.parse()
  grouped = group_by_prefix(args)
  provision(**grouped)