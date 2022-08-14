/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/

import React, {Component} from "react";
import {AgGridReact} from "ag-grid-react";
import "ag-grid-community/dist/styles/ag-grid.css";
import "ag-grid-community/dist/styles/ag-theme-blue.css";
import "bootstrap/js/dist/dropdown";
import "bootstrap/dist/css/bootstrap.css";
import {FaSyncAlt} from "react-icons/fa";

//appsync
import {GraphQLAPI, graphqlOperation} from "@aws-amplify/api-graphql";
import {
    getActionItemsFromTransitNetworkOrchestratorTables,
    getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables,
} from "../../graphql/queries";
import {updateTransitNetworkOrchestratorTable} from "../../graphql/mutations";

import VersionHistoryModal from "./VersionHistoryModal";
import ConfirmRejectModal from "./ConfirmRejectModal";
import ConfirmAcceptModal from "./ConfirmAcceptModal";

class Action extends Component {
  constructor(props) {
    super(props);

    let firstCommaIndex = this.props.location.state.indexOf(",");
    const user = this.props.location.state.substring(0, firstCommaIndex);
    const group = this.props.location.state.substring(firstCommaIndex + 1);

    this.state = {
      currentUser: user.trim(), //this is the user who logged in the console
      currentGroup: group.trim(), //this is the group(s) to which the user belongs
      selectedRow: "",
      selectedSubnetId: "",
      showHistoryModal: false,
      showAcceptConfirmationModal: false,
      showRejectConfirmationModal: false,
      btnAdminActionDisabled: true, //determine button accept or reject. By default it is set to disabled
      btnHistoryDisabled: true, //determine button view history. By default it is set to disabled
      versionHistoryItems: [],
      refresh: false,
      confirmChoice: "",

      //List of attribute/column names from the ddb table
      dataFields: [
        {
          SubnetId: "",
          Version: "",
          Status: "",
          TgwId: "",
          VpcId: "",
          UserId: "",
          RequestTimeStamp: "",
          ResponseimeStamp: "",
          AssociationRouteTable: "",
          PropagationRouteTablesString: "",
          TagEventSource: "",
          Action: "",
          AWSSpokeAccountId: "",
          AWSSpokeAccountName:"",
          TimeToLive: "",
          AvailabilityZone: "",
          VpcCidr: "",
          AdminAction: "",
          Comment: "",
          items: [],
        },
      ],

      //define columns in the grid: field names in the grid should match attribute/column names from the ddb table
      columnDefs: [
        {
          headerName: "VPC Id",
          field: "VpcId",
          width: 220,
          checkboxSelection: true,
        },
        {
          headerName: "VPC CIDR",
          field: "VpcCidr",
        },
        {
          headerName: "Action",
          field: "Action",
        },
        {
          headerName: "Status",
          field: "Status",
          cellClass: function (params) {
            return params.value === "failed" ? "rag-red" : "rag-transparent";
          },
        },
        {
          headerName: "Comment",
          field: "Comment",
          autoHeight: true,
          cellStyle: { "white-space": "normal" },
        },
        {
          headerName: "Association RT",
          field: "AssociationRouteTable",
        },
        {
          headerName: "Propagation RTs",
          field: "PropagationRouteTablesString",
        },
        {
          headerName: "Spoke Account",
          field: "AWSSpokeAccountId",
        },
        {
          headerName: "Spoke Account Name",
          field: "AWSSpokeAccountName"
        },
        {
          headerName: "Subnet Id",
          field: "SubnetId",
          width: 210,
        },
        {
          headerName: "AZ",
          field: "AvailabilityZone",
        },
        {
          headerName: "Tag Event Source",
          field: "TagEventSource",
        },
        {
          headerName: "Request Time",
          field: "RequestTimeStamp",
        },
        {
          headerName: "Response Time",
          field: "ResponseTimeStamp",
        },
        {
          headerName: "User Id",
          field: "UserId",
        },
        {
          headerName: "Transit Gateway Id",
          field: "TgwId",
        },
      ],
    }; //end this.state
  } //end constructor()

  //Refresh action items every 5 minutes by default
  async componentDidMount() {
    //load action items for this first time
    this.getActionItems();

    //auto reload action items every 5 minutes
    this.interval = setInterval(this.getActionItems, 300000);
  }

  //Run GraphQL to fetch action items (status - requested, processing, failed) from the ddb table
  getActionItems = async () => {
    const result = await GraphQLAPI.graphql(
      graphqlOperation(getActionItemsFromTransitNetworkOrchestratorTables)
    );
    this.setState({
      items:
        result.data.getActionItemsFromTransitNetworkOrchestratorTables.items,
    });
  };

  //Run GraphQL to accept or reject request
  processRequest = async (adminAction) => {
    try {
      //get current timestamp
      const currentTimeStamp = new Date();
      const UTCTimeStamp = currentTimeStamp.toISOString();
      this.setState({ selectedSubnetId: this.state.selectedRow.SubnetId });

      const input = {
        SubnetId: this.state.selectedSubnetId,
        Version: "latest",
        Status: "processing",
        UserId: this.state.currentUser,
        GraphQLTimeStamp: UTCTimeStamp,
        AdminAction: adminAction,
      };

      await GraphQLAPI.graphql(
        graphqlOperation(updateTransitNetworkOrchestratorTable, { input })
      );

      this.getActionItems();
    } catch (error) {
      console.error(error);
    }
  }; //end processRequest

  //Run GraphQL to accept or reject request
  showVersionHistory = async () => {
    try {
      this.setState({
        showHistoryModal: true,
        selectedSubnetId: this.state.selectedRow.SubnetId,
      });

      const selectedSubnetId = this.state.selectedRow.SubnetId;

      const filter = {
        SubnetId: { eq: selectedSubnetId },
        Version: { ne: "latest" },
      };
      const result = await GraphQLAPI.graphql(
        graphqlOperation(
          getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables,
          { filter }
        )
      );
      this.setState({
        versionHistoryItems:
          result.data
            .getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables
            .items,
      });
    } catch (error) {
      console.error(error);
    }
  }; //end getVersionHistory

  //handle user's choice of accepting request
  handleAccept = async (choice) => {
    if (choice === "confirm") {
      this.processRequest("accept");
    }
    this.setState({ showAcceptConfirmationModal: false });
  };

  //handle user's choice of rejecting request
  handleReject = async (choice) => {
    if (choice === "confirm") {
      this.processRequest("reject");
    }
    this.setState({ showRejectConfirmationModal: false });
  };

  //initialize grid
  onGridReady = (params) => {
    this.gridApi = params.api;
    this.gridColumnApi = params.columnApi;
    this.autoSizeAll();
    this.gridApi.resetRowHeights();
  };

  //auto adjust column width to fix content
  autoSizeAll() {
    var allColumnIds = [];
    this.gridColumnApi.getAllColumns().forEach(function (column) {
      if (
        column.colId !== "SubnetId" &&
        column.colId !== "VpcId" &&
        column.colId !== "Comment"
      )
        allColumnIds.push(column.colId);
    });
    this.gridColumnApi.autoSizeColumns(allColumnIds);
  }

  //get the selected row
  onRowSelected = (params) => {
    const selectedRows = this.gridApi.getSelectedRows();
    if (selectedRows.length > 0) {
      this.setState({
        selectedRow: selectedRows[0],
        selectedSubnetId: selectedRows[0].SubnetId,
        btnHistoryDisabled: false,
      });
      //Only allow accepting or rejecting request if user is in admin group and the request is not already in processing status
      if (
        this.state.currentGroup.includes("AdminGroup") &&
        selectedRows[0].Status !== "processing"
      ) {
        this.setState({
          btnAdminActionDisabled: false,
        });
      } else {
        this.setState({
          btnAdminActionDisabled: true,
        });
      }
    } //end if (selectedRows.length>0)
    else {
      this.setState({
        selectedRow: "",
        selectedSubnetId: "",
        btnAdminActionDisabled: true,
        btnHistoryDisabled: true,
      });
    }
  };

  //render UI
  render() {
    let closeHistoryModal = () => this.setState({ showHistoryModal: false });

    return (
      <div
        className="ag-theme-blue"
        style={{
          height: "calc(85vh - 50px)",
        }}
      >
        <div className="dropdown">
          <button
            className="btn btn-light dropdown-toggle"
            style={{
              background: "#5d9cd2",
              color: "white",
              fontSize: "10pt",
              margin: "5px",
            }}
            type="button"
            id="dropdownMenuButton"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
          >
            Action
          </button>
          <div
            className="dropdown-menu"
            aria-labelledby="dropdownMenuButton"
            style={{ background: "#e1e4e9", color: "black", fontSize: "10pt" }}
          >
            <button
              id="btn-accept"
              className="dropdown-item"
              disabled={this.state.btnAdminActionDisabled}
              onClick={() =>
                this.setState({ showAcceptConfirmationModal: true })
              }
            >
              Approve
            </button>
            <ConfirmAcceptModal
              show={this.state.showAcceptConfirmationModal}
              onHide={this.handleAccept.bind(this)}
              params={{ action: "accept", selectedRow: this.state.selectedRow }}
            />
            <button
              id="btn-reject"
              className="dropdown-item"
              disabled={this.state.btnAdminActionDisabled}
              onClick={() =>
                this.setState({ showRejectConfirmationModal: true })
              }
            >
              Reject
            </button>
            <ConfirmRejectModal
              show={this.state.showRejectConfirmationModal}
              onHide={this.handleReject.bind(this)}
              params={{ action: "reject", selectedRow: this.state.selectedRow }}
            />
            <button
              id="btn-history"
              className="dropdown-item"
              disabled={this.state.btnHistoryDisabled}
              onClick={() => this.showVersionHistory()}
            >
              View History
            </button>
            <VersionHistoryModal
              show={this.state.showHistoryModal}
              onHide={closeHistoryModal}
              params={{
                selectedSubnetId: this.state.selectedSubnetId,
                versionHistoryItems: this.state.versionHistoryItems,
              }}
            />
          </div>
          <div className="divright">
            <button
              id="btn-refresh-action"
              style={{ background: "#5d9cd2", color: "white" }}
              onClick={() => this.getActionItems()}
            >
              <FaSyncAlt />
            </button>
          </div>
        </div>
        <AgGridReact
            onGridReady={this.onGridReady}
            rowSelection="single"
            defaultColDef={{resizable: true, sortable: true, filter: true}}
            columnDefs={this.state.columnDefs}
            rowData={this.state.items}
            onRowSelected={this.onRowSelected}
        />
      </div>
    );
  } //end render
} //end class
export default Action;
