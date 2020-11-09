import React from 'react';

import {makeStyles} from '@material-ui/core/styles';
import Link from '@material-ui/core/Link';
import Grid from '@material-ui/core/Grid';
import Box from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
import ButtonGroup from '@material-ui/core/ButtonGroup';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import Slide from '@material-ui/core/Slide';

import {API, graphqlOperation} from "aws-amplify";
import {
    getDashboarItemsFromTransitNetworkOrchestratorTables,
    getDashboarItemsForStatusFromTransitNetworkOrchestratorTables,
    getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables
} from "../graphql/queries";

import Title from './Title';
import HistoryTable from "./HistoryTable";
import TransitGatewayTable from "./TransitGatewayTable";

function preventDefault(event) {
    event.preventDefault();
}

const useStyles = makeStyles((theme) => ({
    seeMore: {
        marginTop: theme.spacing(3),
    },
}));

const Transition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

export default function TransitGatewayEntries() {
    const classes = useStyles();

    const [dialogOpen, setDialogOpen] = React.useState(false);
    let [versionHistoryItems, setVersionHistoryItems] = React.useState(false);
    const handleClickOpen = async (row) => {
        try {
            console.log(`Fetching history for selected attachment...`);
            const filter = {SubnetId: {eq: row.SubnetId}, Version: {ne: "latest"}};
            let graphQlOptions = graphqlOperation(getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables, {filter});
            graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
            const result = await API.graphql(graphQlOptions);
            setVersionHistoryItems(result.data.getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables.items);
        } catch (error) {
            console.error(error);
        }
        setDialogOpen(true);
    };
    const handleClose = () => {
        setDialogOpen(false);
    };

    let [items, setItems] = React.useState([]);
    // Get all the attachments
    const getTgwAttachments = async (statuses) => {
        console.log(`Fetching the TGW attachments for status ${statuses}...`);
        let graphQlOptions;
        if (statuses) {
            const filter = {Status: {eq: statuses}, Version: {ne: "latest"}};
            graphQlOptions = graphqlOperation(getDashboarItemsForStatusFromTransitNetworkOrchestratorTables, {filter});
            graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
            const result = await API.graphql(graphQlOptions);
            setItems(result.data.getDashboarItemsForStatusFromTransitNetworkOrchestratorTables.items);
        }
        else {
            graphQlOptions = graphqlOperation(getDashboarItemsFromTransitNetworkOrchestratorTables);
            graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
            const result = await API.graphql(graphQlOptions);
            setItems(result.data.getDashboarItemsFromTransitNetworkOrchestratorTables.items);
        }
        console.log(`Finished fetching the TGW attachments`);
    };
    React.useEffect(getTgwAttachments,[]);

    // render the table
    return (
        <React.Fragment>
            <Title>Attachments</Title>
            <Grid container>
                <Box pt={1} pb={1}>
                    <ButtonGroup variant="contained" color="primary" aria-label="contained primary button group">
                        <Button onClick={() => {getTgwAttachments()}}>All</Button>
                        <Button onClick={() => {getTgwAttachments('approved')}}>Approved</Button>
                        <Button onClick={() => {getTgwAttachments('auto-approved')}}>Auto Approved</Button>
                        <Button onClick={() => {getTgwAttachments('rejected')}}>Rejected</Button>
                        <Button onClick={() => {getTgwAttachments('auto-rejected')}}>Auto Rejected</Button>
                        <Button onClick={() => {getTgwAttachments('failed')}}>Failed</Button>
                    </ButtonGroup>
                </Box>
            </Grid>
            {TransitGatewayTable(items, 'attachments', handleClickOpen)}
            <div className={classes.seeMore}>
                <Link color="primary" href="#" onClick={preventDefault}>
                    See more attachments
                </Link>
            </div>

            <Dialog
                open={dialogOpen}
                TransitionComponent={Transition}
                keepMounted
                onClose={handleClose}
                fullWidth={true}
                maxWidth = {'xl'}
                aria-labelledby="alert-dialog-slide-title"
                aria-describedby="alert-dialog-slide-description">
                <DialogTitle id="alert-dialog-slide-title">{"Viewing version history"}</DialogTitle>
                <DialogContent>
                    {HistoryTable(versionHistoryItems)}
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={handleClose} color="primary">
                        Close
                    </Button>
                </DialogActions>
            </Dialog>
        </React.Fragment>
    );
}
