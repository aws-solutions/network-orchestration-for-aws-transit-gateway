/*********************************************************************************************************************
 *  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance        *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                                    *
 *                                                                                                                    *
 *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import React, {Component} from "react";
import {Modal, Button} from 'react-bootstrap';

class ConfirmRejectModal extends Component {
  
    constructor(props) {
        super(props);
    
        this.state = {
            items:[]
        }//end this.state
    }//end constructor()

    async componentDidMount(){ 
      this.setState({items:this.props.params.selectedRow});
     
    }

    btnCancelClick(){
      this.props.onHide("cancel");
    }

    btnConfirmClick(){

      this.props.onHide("confirm");
    }

    //render UI
    render() {

        return (
          <Modal
            {...this.props}
            size="lg"
            aria-labelledby="contained-modal-title-vcenter"
            centered
          >
            <Modal.Header closeButton>
              <Modal.Title id="contained-modal-title-vcenter">
                Confirmation
              </Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <div >
                    <h4>
                    Are you sure you want to {this.props.params.action} this request?
                    </h4>
                    <div style={{background: "#FFFFE0"}}>
                        <p>
                            <b>Transit Gateway Id:</b> {this.props.params.selectedRow.TgwId}
                            <br></br>
                            <b>Subnet Id:</b> {this.props.params.selectedRow.SubnetId}
                            <br></br>
                            <b>VPC Id:</b> {this.props.params.selectedRow.VpcId}
                            <br></br>
                            <b>Status:</b> {this.props.params.selectedRow.Status}
                            <br></br>
                            <b>VPC CIDR:</b> {this.props.params.selectedRow.VpcCidr}
                            <br></br>
                            <b>Availability Zone:</b> {this.props.params.selectedRow.AvailabilityZone}
                            <br></br>
                            <b>Association RT:</b> {this.props.params.selectedRow.AssociationRouteTable}
                            <br></br>
                            <b>Propagation RTs:</b> {this.props.params.selectedRow.PropagationRouteTablesString}
                            <br></br>
                            <b>Tag Event Source:</b> {this.props.params.selectedRow.TagEventSource}
                            <br></br>
                            <b>Spoke Account:</b> {this.props.params.selectedRow.AWSSpokeAccountId}
                            <br></br>
                            <b>Action:</b> {this.props.params.selectedRow.Action}
                            <br></br>
                            <b>User Id:</b> {this.props.params.selectedRow.UserId}
                            <br></br>
                            <b>Request Time:</b> {this.props.params.selectedRow.RequestTimeStamp}
                            <br></br>
                            <b>Response Time:</b> {this.props.params.selectedRow.ResponseTimeStamp}
                            <br></br>
                            <b>Comment</b> {this.props.params.selectedRow.Comment}
                        </p>
                    </div>
                </div>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={this.btnCancelClick.bind(this)}>Cancel</Button>
              <Button variant="primary" onClick={this.btnConfirmClick.bind(this)}>Reject</Button>
            </Modal.Footer>
          </Modal>
        );
        
      }//end render
    
}//end class

export default ConfirmRejectModal;