import React from 'react';

import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';
import TableBody from '@material-ui/core/TableBody';
import Box from '@material-ui/core/Box';
import Tooltip from '@material-ui/core/Tooltip';
import Table from '@material-ui/core/Table';
import IconButton from '@material-ui/core/IconButton';
import HistoryIcon from '@material-ui/icons/History';
import ApproveIcon from '@material-ui/icons/CheckCircle';
import RejectIcon from '@material-ui/icons/Cancel';

import StatusTableCell from "./StatusTableCell";

export default function TransitGatewayTable(items, viewType, actionCallback) {
    return (
        <Table size="medium" stickyHeader={true}>
            <TableHead>
                <TableRow>
                    <TableCell>Actions</TableCell>
                    <TableCell>VPC <br/> VPC CIDR</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Comment</TableCell>
                    <TableCell>Association RT<br/> Propagation RT</TableCell>
                    <TableCell>Spoke Account</TableCell>
                    <TableCell>Subnet<br/>AZ</TableCell>
                    <TableCell>Tag event source</TableCell>
                    <TableCell>Request Ts<br/> Response Ts</TableCell>
                    <TableCell>User ID</TableCell>
                    <TableCell align="right">TGW ID</TableCell>
                </TableRow>
            </TableHead>
            <TableBody>
                {items.map((row) => (
                    <TableRow key={row.id}>
                        <TableCell>
                            <Box>
                                <Tooltip title="View History" placement="right">
                                    <IconButton onClick={() => {actionCallback(row, 'history')}}>
                                        <HistoryIcon style={{fill: "#ff5722"}}/>
                                    </IconButton>
                                </Tooltip>
                                {(() => {
                                    if (row.Status !== 'processing' && viewType === 'actions')
                                        return (
                                            <Box>
                                                <Tooltip title="Accept" placement="right">
                                                    <IconButton onClick={() => {actionCallback(row, 'accept')}}>
                                                        <ApproveIcon style={{fill: "green"}}/>
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Reject" placement="right">
                                                    <IconButton onClick={() => {actionCallback(row, 'reject')}}>
                                                        <RejectIcon style={{fill: "red"}}/>
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        )
                                })()}
                            </Box>
                        </TableCell>
                        <TableCell>{row.VpcId}
                            <br/>
                            {row.VpcCidr}
                        </TableCell>
                        <TableCell>{row.Action}</TableCell>
                        <TableCell>
                            {StatusTableCell(row)}
                        </TableCell>
                        <TableCell>{row.Comment}</TableCell>
                        <TableCell>A={row.AssociationRouteTable}
                            <br/>
                            P={row.PropagationRouteTablesString}
                        </TableCell>
                        <TableCell>{row.AWSSpokeAccountId}</TableCell>
                        <TableCell>{row.SubnetId}
                            <br/>
                            {row.AvailabilityZone}
                        </TableCell>
                        <TableCell>{row.TagEventSource}</TableCell>
                        <TableCell>{row.RequestTimeStamp}
                            <br/>
                            {row.ResponseTimeStamp}
                        </TableCell>
                        <TableCell>{row.UserId}</TableCell>
                        <TableCell align="right">{row.TgwId}</TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    );
}
