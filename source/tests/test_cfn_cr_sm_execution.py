import lambda_custom_resource
import botocore.exceptions
from os import environ
from lib.logger import Logger
logger = Logger('info')

context = {}
event = {
    "version": "0",
    "id": "c888c3f4-fbeb-928d-5cb6-ea174474ffa4",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": "123456789012",
    "time": "2019-05-23T16:57:03Z",
    "region": "us-east-1",
    "resources": [
        "arn:aws:ec2:us-east-1:123456789012:subnet/subnet-abcd123"
    ],
    "detail": {
        "changed-tag-keys": [
            "attach-to-flat"
        ],
        "service": "ec2",
        "resource-type": "subnet",
        "version": 1.0,
        "tags": {
            "AWS_Solutions": "LandingZoneStackSet",
            "Network": "Public",
            "aws:cloudformation:logical-id": "PublicSubnet1",
            "attach-to-flat": "flat-100",
            "Name": "Public subnet 1"
        }
    }
}


def test_cfn_trigger_state_machine(mocker):
    state_machine_arn = 'arn:aws:states:us-east-1:xxxx:execution:TestStateMachine'
    environ['STATE_MACHINE_ARN'] = state_machine_arn

    # Test expect failure
    # "EXCEPTION": "An error occurred (InvalidArn) when calling the StartExecution operation:
    # Invalid Arn: 'Resource type not valid in this context: execution'"
    try:
        lambda_custom_resource.lambda_handler(event, context)
        raise RuntimeError('As the ARN is invalid this should fail')
    except botocore.exceptions.ClientError as err:
        logger.info(err.response['Error']['Code'])