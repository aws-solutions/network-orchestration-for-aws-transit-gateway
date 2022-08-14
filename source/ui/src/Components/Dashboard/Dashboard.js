/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/

import React, { Component } from "react";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/dist/styles/ag-grid.css";
import "ag-grid-community/dist/styles/ag-theme-blue.css";
import { FaSyncAlt } from "react-icons/fa";
import VersionHistoryModal from "../Action/VersionHistoryModal";

//appsync
import { GraphQLAPI, graphqlOperation } from "@aws-amplify/api-graphql";
import {
  getDashboardItemsFromTransitNetworkOrchestratorTables,
  getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables,
} from "../../graphql/queries";

class Dashboard extends Component {
  constructor(props) {
    super(props);

    this.state = {
      selectedRow: "",
      selectedSubnetId: "",
      showHistoryModal: false,
      btnDisabled: true,

      //List attribute/column names from the ddb table
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
          cellClassRules: {
            "rag-red": function (params) {
              return (
                params.value === "rejected" || params.value === "auto-rejected"
              );
            },
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
          field: "AWSSpokeAccountName",
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

  //Refresh dashboard every 5 minutes by default
  async componentDidMount() {
    this.getDashboardItems();
    this.interval = setInterval(this.getDashboardItems, 300000);
  }

  //Run GraphQL to fetch dashboard items from the ddb table
  getDashboardItems = async () => {
    try {
      const result = await GraphQLAPI.graphql(
        graphqlOperation(getDashboardItemsFromTransitNetworkOrchestratorTables)
      );
      this.setState({
        items:
          result.data.getDashboardItemsFromTransitNetworkOrchestratorTables
            .items,
      });
    } catch (error) {
      console.error(error);
    }
  };

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

  //get the selected row
  onRowSelected = (params) => {
    const selectedRows = this.gridApi.getSelectedRows();
    if (selectedRows.length > 0) {
      this.setState({
        selectedRow: selectedRows[0],
        selectedSubnetId: selectedRows[0].SubnetId,
        btnDisabled: false,
      });
    } else {
      this.setState({
        selectedRow: "",
        selectedSubnetId: "",
        btnDisabled: true,
      });
    }
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
  render() {
    let closeHistoryModal = () => this.setState({ showHistoryModal: false });

    return (
      <div
        className="ag-theme-blue"
        style={{
          height: "calc(85vh - 50px)",
        }}
      >
        <div>
          <button
            id="btn-history"
            className="btn btn-light"
            disabled={this.state.btnDisabled}
            style={{
              background: "#5d9cd2",
              color: "white",
              margin: "5px",
              fontSize: "10pt",
            }}
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
          <button
            id="btn-refresh-action"
            className="divright"
            style={{ background: "#5d9cd2", color: "white" }}
            onClick={() => this.getDashboardItems()}
          >
            <FaSyncAlt />
          </button>
        </div>
        <AgGridReact
          onGridReady={this.onGridReady}
          rowSelection="single"
          defaultColDef={{ resizable: true, sortable: true, filter: true }}
          columnDefs={this.state.columnDefs}
          rowData={this.state.items}
          onRowSelected={this.onRowSelected}
        ></AgGridReact>
      </div>
    );
  }
}
export default Dashboard;
