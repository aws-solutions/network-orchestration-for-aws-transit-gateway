import React from 'react';

import Table from '@material-ui/core/Table';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';
import TableBody from '@material-ui/core/TableBody';
import Box from '@material-ui/core/Box';

import StatusTableCell from './StatusTableCell';

export default function HistoryTable(versionHistoryItems) {
    return (
        <Box>
            <Table size="medium" stickyHeader={true}>
                <TableHead>
                    <TableRow>
                        <TableCell>VPC</TableCell>
                        <TableCell>Action</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Comment</TableCell>
                        <TableCell>Association RT<br/> Propagation RT</TableCell>
                        <TableCell>Spoke Account</TableCell>
                        <TableCell>Subnet<br/>AZ</TableCell>
                        <TableCell>Tag event source</TableCell>
                        <TableCell>Request Ts<br/> Response Ts</TableCell>
                        <TableCell align="right">User ID</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {versionHistoryItems && versionHistoryItems.map((row) => (
                        <TableRow key={row.id}>
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
                            <TableCell align="right">{row.UserId}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </Box>
    );
}
