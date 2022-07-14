/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/

import React, {Component} from "react";
import {Button, Modal} from "react-bootstrap";

class ConfirmAcceptModal extends Component {
  constructor(props) {
    super(props);

    this.state = {
      items: [],
    }; //end this.state
  } //end constructor()

  async componentDidMount() {
    this.setState({ items: this.props.params.selectedRow });
  }

  btnCancelClick() {
    this.props.onHide("cancel");
  }

  btnConfirmClick() {
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
          <div>
            <h4>Are you sure you want to accept this request?</h4>
            <div style={{ background: "#FFFFE0" }}>
              <p>
                <b>Transit Gateway Id:</b> {this.props.params.selectedRow.TgwId}
                <br/>
                <b>Subnet Id:</b> {this.props.params.selectedRow.SubnetId}
                <br/>
                <b>VPC Id:</b> {this.props.params.selectedRow.VpcId}
                <br/>
                <b>Status:</b> {this.props.params.selectedRow.Status}
                <br/>
                <b>VPC CIDR:</b> {this.props.params.selectedRow.VpcCidr}
                <br/>
                <b>Availability Zone:</b>{" "}
                {this.props.params.selectedRow.AvailabilityZone}
                <br/>
                <b>Association RT:</b>{" "}
                {this.props.params.selectedRow.AssociationRouteTable}
                <br/>
                <b>Propagation RTs:</b>{" "}
                {this.props.params.selectedRow.PropagationRouteTablesString}
                <br/>
                <b>Tag Event Source:</b>{" "}
                {this.props.params.selectedRow.TagEventSource}
                <br/>
                <b>Spoke Account:</b>{" "}
                {this.props.params.selectedRow.AWSSpokeAccountId}
                <br/>
                <b>Action:</b> {this.props.params.selectedRow.Action}
                <br/>
                <b>User Id:</b> {this.props.params.selectedRow.UserId}
                <br/>
                <b>Request Time:</b>{" "}
                {this.props.params.selectedRow.RequestTimeStamp}
                <br/>
                <b>Response Time:</b>{" "}
                {this.props.params.selectedRow.ResponseTimeStamp}
                <br/>
                <b>Comment</b> {this.props.params.selectedRow.Comment}
              </p>
            </div>
          </div>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={this.btnCancelClick.bind(this)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={this.btnConfirmClick.bind(this)}>
            Approve
          </Button>
        </Modal.Footer>
      </Modal>
    ); //end return
  } //end render
} //end class

export default ConfirmAcceptModal;
