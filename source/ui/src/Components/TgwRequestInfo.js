import React from 'react';

import Grid from '@material-ui/core/Grid';
import Paper from '@material-ui/core/Paper';
import {Box} from '@material-ui/core';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableRow from '@material-ui/core/TableRow';
import TableCell from '@material-ui/core/TableCell';


export default function TgwRequestInfo(request, classes) {
    console.log(`Showing Tgw request info`);
    return (
        <div className={classes.root}>
            <Grid container spacing={1}>
                <Grid item xs={12} sm={6}>
                    <Paper className={classes.paper}>
                        <Box><h4>Request Details</h4></Box>
                        <Table size="medium">
                            <TableBody>
                                <TableRow>
                                    <TableCell>Transit Gateway Id:</TableCell>
                                    <TableCell>{request.TgwId}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Status:</TableCell>
                                    <TableCell>{request.Status}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>User Id:</TableCell>
                                    <TableCell>{request.UserId}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Action:</TableCell>
                                    <TableCell>{request.Action}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Comment:</TableCell>
                                    <TableCell>{request.Comment}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Request Ts:</TableCell>
                                    <TableCell>{request.RequestTimeStamp}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Response Ts:</TableCell>
                                    <TableCell>{request.ResponseTimeStamp}</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </Paper>
                </Grid>
                <Grid item xs={12} sm={6}>
                    <Paper className={classes.paper}>
                        <Box><h4>Networking Details</h4></Box>
                        <Table size="medium">
                            <TableBody>
                                <TableRow>
                                    <TableCell>Spoke Account Id:</TableCell>
                                    <TableCell>{request.AWSSpokeAccountId}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>VPC Id:</TableCell>
                                    <TableCell>{request.VpcId}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>VPC Cidr:</TableCell>
                                    <TableCell>{request.VpcCidr}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Subnet Id:</TableCell>
                                    <TableCell>{request.SubnetId}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Association RT:</TableCell>
                                    <TableCell>{request.AssociationRouteTable}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Propagation RTs:</TableCell>
                                    <TableCell>{request.PropagationRouteTablesString}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Availability Zone:</TableCell>
                                    <TableCell>{request.AvailabilityZone}</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell>Tag event source:</TableCell>
                                    <TableCell>{request.TagEventSource}</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </Paper>
                </Grid>
            </Grid>
        </div>
    );
}
