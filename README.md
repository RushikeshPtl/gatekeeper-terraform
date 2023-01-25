# Gatekeeper

Gatekeeper consists of all the APIs, State Machines and cloud based resources based on AWS SAM.

## Requirements

- [EditorConfig for VS Code](https://marketplace.visualstudio.com/items?itemName=EditorConfig.EditorConfig)

- [python +3.9](https://www.python.org/downloads/)

- [aws-vault](https://github.com/99designs/aws-vault)

- [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and IAM credentials

- [terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)

- [terragrunt](https://terragrunt.gruntwork.io/docs/getting-started/install/)

## Lambda Functions on AWS

Basic setup:

- Python code:
  - simple code on aws-console or a zip file uploaded to S3 for bigger apps
  - every library outside the standard library must be included in the zip file
  - you need a handler for Lambda, in this case we use Mangum
- API gateway to trigger the lambda function
  - gateway URL used as a proxy to pass requests to the app router
  - permissions for gateway: in this case will be public.

---

## Deploys the project
1. Provides your credentials
```sh
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
```
2. Replaces **/src** with the code of your Python App
3. Downloads required packages

```sh
make install
```

4. Creates a bucket to store state files. The bucket name is specify in `env/dev/env_vars.hcl`(for development environment).
5. Creates a DynamoDB table to lock state with hash key is `LockID` and type `S`.
6. Deploys (`dev` environment):

```sh
cd ./env/dev/us-east-1
terragrunt run-all apply
```
or
```sh
cd ./env/dev/us-east-1
make apply
```

7. Gets base url to access api gateway
   ![Base URL](/images/api_gateway_base_url.png)

## Terraform secrets

Terraform will require the following variables to plan and apply:

```hcl
AWS_ACCESS_KEY_ID             # AWS access key associated with an IAM user or role.
AWS_SECRET_ACCESS_KEY         # Secret key associated with the access key. This is essentially the "password" for the access key
```
