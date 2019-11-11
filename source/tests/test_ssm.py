from moto import mock_ssm
import botocore.exceptions
from lib.logger import Logger
from lib.ssm import SSM
logger = Logger('critical')
ssm = SSM(logger)


@mock_ssm
def test_put_parameter_secure_default_kms():

    ssm.put_parameter('test', 'value', 'A test parameter', 'SecureString')

    response = ssm.get_parameter('test')

    assert (response['Parameter']) is not None
    assert response['Parameter']['Name'] == 'test'
    assert response['Parameter']['Value'] == 'value'
    assert response['Parameter']['Type'] == 'SecureString'


@mock_ssm
def test_delete_parameter():

    ssm.put_parameter(
        'test',
        'A test parameter',
        'value',
        'SecureString')

    # query the parameter before deleting it
    response = ssm.get_parameter('test')
    assert (response['Parameter']) is not None

    # deleting the parameter
    ssm.delete_parameter('test')

    # testing the exception after the parameter is deleted and we try _get_ function
    try:
        ssm.get_parameter('test')
        raise RuntimeError('As this parameter has been deleted, this should fail')
    except botocore.exceptions.ClientError as err:
        assert err.operation_name == 'GetParameter'
