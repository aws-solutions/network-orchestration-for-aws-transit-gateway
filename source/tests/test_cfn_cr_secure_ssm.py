from moto import mock_ssm
import botocore.exceptions
import lambda_custom_resource
from lib.logger import Logger
from lib.ssm import SSM
logger = Logger('critical')
ssm = SSM(logger)

context = {}
event = {
    "ResourceType": "Custom::SecureSSMStrings",
    "PhysicalResourceId": "physical_resource_id",
    "ResourceProperties": {
        "PSKey": "/parameter/store/test/key",
        "PSValue": "test-value",
        "PSDescription": "a test description"
    }
}


@mock_ssm
def test_secure_ssm_parameter_create():
    lambda_custom_resource.create(event, context)

    response = ssm.get_parameter('/parameter/store/test/key')

    assert (response['Parameter']) is not None
    assert response['Parameter']['Name'] == '/parameter/store/test/key'
    assert response['Parameter']['Value'] == 'test-value'
    assert response['Parameter']['Type'] == 'SecureString'

@mock_ssm
def test_secure_ssm_parameter_update():
    lambda_custom_resource.update(event, context)

    response = ssm.get_parameter('/parameter/store/test/key')

    assert (response['Parameter']) is not None
    assert response['Parameter']['Name'] == '/parameter/store/test/key'
    assert response['Parameter']['Value'] == 'test-value'
    assert response['Parameter']['Type'] == 'SecureString'

@mock_ssm
def test_secure_ssm_parameter_delete():
    lambda_custom_resource.create(event, context)

    response = ssm.get_parameter('/parameter/store/test/key')
    assert (response['Parameter']) is not None

    lambda_custom_resource.delete(event, context)

    # testing the exception after the parameter is deleted and we try _get_ function
    try:
        ssm.get_parameter('/parameter/store/test/key')
        raise RuntimeError('As this parameter has been deleted, this should fail')
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == 'GetParameter'

