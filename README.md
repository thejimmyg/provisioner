# Provisioner

Work in progress. Please don't use yet.

## Install Locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Test

```
source .venv/bin/activate
coverage run -m unittest discover && coverage report && coverage html
```

After running the above, take a look at coverage in an HTML report like this:

```
open htmlcov/index.html
```

To only run the unit tests:

```
coverage run -m unittest test.py && coverage report && coverage html
```

## Example

```
% python3 example.py --help
usage: example.py [-h] --region REGION --account ACCOUNT --user USER --cloudformation-bucket CLOUDFORMATION_BUCKET
                  [--stack-name-prefix STACK_NAME_PREFIX] [--global-postfix GLOBAL_POSTFIX] --issuer ISSUER --audience
                  AUDIENCE --oauth-token-url OAUTH_TOKEN_URL --oauth-authorize-url OAUTH_AUTHORIZE_URL --frontend-bucket
                  FRONTEND_BUCKET --company-two-api-url COMPANY_TWO_API_URL --company-one-api-url COMPANY_ONE_API_URL

options:
  -h, --help            show this help message and exit

aws:
  Verify that the account and credentials being used match the expected values set by these flags

  --region REGION       expected AWS region e.g. eu-west-2
  --account ACCOUNT     expected 12 digit AWS account number e.g. 000000000000
  --user USER           expected AWS user as obtained from 'aws sts get-caller-identity' e.g. AKIAIOSFODNN7EXAMPLE

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

oidc:
  Settings for authorising a user via OIDC

  --issuer ISSUER       the issuer for the JWT Authorizer
  --audience AUDIENCE   the audience for the JWT Authorizer
  --oauth-token-url OAUTH_TOKEN_URL
                        the OAuth 2.0 token endpoint
  --oauth-authorize-url OAUTH_AUTHORIZE_URL
                        the OAuth 2.0 authorize endpoint

frontend:
  Frontend SPA settings

  --frontend-bucket FRONTEND_BUCKET
                        S3 bucket name for publicly served front-end assets like app.css and app.js

publisher:
  Settings affecting all stacks that make up this application

  --company-two-api-url COMPANY_TWO_API_URL
                        The URL of the company/two API endpoint
  --company-one-api-url COMPANY_ONE_API_URL
                        The URL of the company/one API endpoint
% localstack start -d
% export AWS_ACCESS_KEY_ID=test
% export AWS_SECRET_ACCESS_KEY=test
% python3 example.py --region eu-west-2 --user AKIAIOSFODNN7EXAMPLE --account 000000000000 --cloudformation-bucket bucket --issuer http://localhost --audience app --oauth-token-url http://localhost/oauth/token --oauth-authorize-url http://localhost/oauth/authorize --frontend-bucket frontend --company-two-api-url http://two.localhost --company-one-api-url http://one.localhost
{'aws': {'account': '000000000000',
         'region': 'eu-west-2',
         'user': 'AKIAIOSFODNN7EXAMPLE'},
 'frontend': {'frontend_bucket': 'frontend'},
 'oidc': {'audience': 'app',
          'issuer': 'http://localhost',
          'oauth_authorize_url': 'http://localhost/oauth/authorize',
          'oauth_token_url': 'http://localhost/oauth/token'},
 'options': {'help': None},
 'positional arguments': {},
 'publisher': {'company_two_api_url': 'http://two.localhost',
               'company_one_api_url': 'http://one.localhost'},
 'stackprovisioner': {'cloudformation_bucket': 'bucket',
                      'global_postfix': '',
                      'stack_name_prefix': ''}}
Created the bucket and enabled versioning.
```

## TODO

- [ ] URL validation in arguments
- [ ] Describe stack call
