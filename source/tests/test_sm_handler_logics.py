from state_machine_handler import VPC
from lib.logger import Logger
logger = Logger('info')

subnet_id = "subnet-039fe0edba0ca443e"

event = {
    "version": "0",
    "id": "cb970a86-f1c9-3f29-91fe-cf556be2816b",
    "detail-type": "Tag Change on Resource",
    "source": "aws.tag",
    "account": 'account_id',
    "time": "2019-05-28T08:01:13Z",
    "region": "us-east-1",
    "resources": [
        "arn:aws:ec2:us-east-1:account_id:subnet/" + subnet_id
    ],
    "detail": {
        "changed-tag-keys": [
            "Associate-with"
        ],
        "service": "ec2",
        "resource-type": "subnet",
        "version": 4.0,
        "tags": {
            "AWS_Solutions": "LandingZoneStackSet",
            "Network": "Private",
            "aws:cloudformation:logical-id": "PrivateSubnet3A",
            "Associate-with": "",
            "Name": "Private subnet 3A"
        }
    }
}


def test_subnet_split():
    vpc = VPC(event, logger)
    response = vpc._extract_resource_id()
    assert response == subnet_id

