from lib.logger import Logger
from lib.state_machine import StateMachine
logger = Logger('critical')
sfn = StateMachine(logger)

trigger_state_machine_response = {"executionArn": "arn:aws:states:us-east-1:xxxx:execution:TestStateMachine:test-execution-name",
                                  "startDate": "yyyy-mm-dd"
                                  }

# declare variables
state_machine_arn = 'arn:aws:states:us-east-1:xxxx:execution:TestStateMachine'
input = {}
name = 'test-execution-name'

def test_trigger_state_machine(mocker):
    mocker.patch.object(sfn, 'trigger_state_machine')
    sfn.trigger_state_machine.return_value = trigger_state_machine_response
    response = sfn.trigger_state_machine(state_machine_arn, input, name)
    assert response.get('executionArn') == "%s:%s" % (state_machine_arn, name)