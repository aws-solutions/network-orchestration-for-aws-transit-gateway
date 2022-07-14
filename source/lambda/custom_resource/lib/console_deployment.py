import json
import logging
from os import environ, path

from botocore.exceptions import ClientError


class ConsoleDeployment:
    """Deploys the STNO Console web application to an S3 bucket"""
    
    def __init__(self, s3_client, open_fn, exists_fn):
        self.logger = logging.getLogger(__name__)
        self.s3_client = s3_client
        self.open_fn = open_fn
        self.exists_fn = exists_fn

    def deploy(self, event):
        """Handler for STNO web ui deployment

        Args:
            event (dict): event from CloudFormation on create, update or delete

        Returns:
            None
        """
        if event["RequestType"] == "Create" or event["RequestType"] == "Update":

            file_path = path.join(
                path.dirname(__file__), "../../console-manifest.json"
            )
            self.logger.debug("file path for console manifest: %s", file_path)

            if self.exists_fn(file_path):
                properties = event["ResourceProperties"]
                self.__copy_ui_files_to_console_bucket(file_path, properties)
                self.__create_stno_config_file(properties)
            else:
                self.logger.error("console manifest file not found")
                raise FileNotFoundError("console manifest file not found")
        else:
            return False

    def __create_stno_config_file(self, properties):
        stno_config_javascript = self.__generate_stno_config_content(properties)
        console_bucket = properties.get("ConsoleBucket")
        self.__upload_stno_config_to_console_bucket(console_bucket, stno_config_javascript)

    def __generate_stno_config_content(self, properties):
        # generate stno_config.js file
        domain_prefix = properties.get("AwsCognitoDomainPrefix")
        aws_region = environ.get("AWS_REGION")
        user_pool_web_client_id = properties.get("AwsUserPoolsWebClientId")
        cognito_identity_pool_id = properties.get("AwsCognitoIdentityPoolId")
        content_delivery_url = properties.get("AwsContentDeliveryUrl")
        content_delivery_bucket = properties.get("AwsContentDeliveryBucket")
        user_pool_id = properties.get("AwsUserPoolsId")
        graph_ql_endpoint = properties.get("AwsAppsyncGraphqlEndpoint")
        self.logger.debug("read properties for stno config object")
        stno_config = {
            "aws_project_region": aws_region,
            "aws_cognito_region": aws_region,
            "aws_user_pools_id": user_pool_id,
            "aws_user_pools_web_client_id": user_pool_web_client_id,
            "aws_cognito_identity_pool_id": cognito_identity_pool_id,
            "aws_appsync_graphqlEndpoint": graph_ql_endpoint,
            "aws_appsync_region": aws_region,
            "aws_appsync_authenticationType": "AMAZON_COGNITO_USER_POOLS",
            "aws_content_delivery_bucket": content_delivery_bucket,
            "aws_content_delivery_bucket_region": aws_region,
            "aws_content_delivery_url": content_delivery_url,
            "website_bucket": content_delivery_bucket,
            "Storage": {
                "region": aws_region,
                "bucket": content_delivery_bucket
            },
            "Auth": {
                "region": aws_region,
                "userPoolId": user_pool_id,
                "userPoolWebClientId": user_pool_web_client_id,
                "mandatorySignIn": True,
                "oauth": {
                    "domain": domain_prefix + ".auth." + aws_region + ".amazoncognito.com",
                    "scope": [
                        "phone",
                        "email",
                        "openid",
                        "profile",
                        "aws.cognito.signin.user.admin"
                    ],
                    "redirectSignIn": content_delivery_url + "/",
                    "redirectSignOut": content_delivery_url + "/",
                    "responseType": "code",
                    "clientId": user_pool_web_client_id
                }
            }
        }

        self.logger.debug("created stno config object")
        stno_config_javascript = (
                "window.stno_config = " + json.dumps(stno_config) + ";"
        )
        return stno_config_javascript

    def __upload_stno_config_to_console_bucket(self, console_bucket, stno_config_javascript):
        key = "console/assets/stno_config.js"
        self.logger.debug("Creating " + key + " in " + console_bucket)
        try:
            self.s3_client.put_object(
                Bucket=console_bucket,
                Key=key,
                Body=stno_config_javascript,
                ContentType="text/javascript",
                Metadata={
                    'Content-Type': "text/javascript"
                }
            )
        except ClientError as err:
            self.logger.error(str(err))
            raise

    def __copy_ui_files_to_console_bucket(self, file_path, properties):
        with self.open_fn(file_path, "r") as json_data:
            console_manifest = json.load(json_data)
        console_bucket = properties.get("ConsoleBucket")
        source_bucket = properties.get("SrcBucket")
        key_prefix = properties.get("SrcPath") + "/"
        for file in console_manifest["files"]:
            key = "console/" + file
            self.s3_client.copy_object(
                CopySource={
                    "Bucket": source_bucket,
                    "Key": key_prefix + key,
                },
                Bucket=console_bucket,
                Key=key,
            )
        self.logger.debug("copying of Console assets successful")
