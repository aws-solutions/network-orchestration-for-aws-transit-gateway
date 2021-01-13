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
import Slide from '@material-ui/core/Slide';
import IconButton from '@material-ui/core/IconButton';
import RefreshIcon from '@material-ui/icons/Refresh';
import Tooltip from '@material-ui/core/Tooltip';

import {API, graphqlOperation} from 'aws-amplify';
import {
    getDashboarItemsFromTransitNetworkOrchestratorTables,
    getDashboarItemsForStatusFromTransitNetworkOrchestratorTables,
    getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables
} from '../graphql/queries';

import Title from './Title';
import HistoryTable from './HistoryTable';
import TransitGatewayTable from './TransitGatewayTable';
import {NotificationEventEmitter} from "./NotificationsTray";

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
            const data = result.data.getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables.items;
            data.forEach(item => item.id = `${item.TgwId}_${item.VpcId}_${item.RequestTimeStamp}`);
            setVersionHistoryItems(data);
        } catch (error) {
            console.error(error);
            const msg = `Error getting version history for subnet ID ${row.SubnetId} <br> Error: ${error.errors[0].errorType} <br> Message: ${error.errors[0].message}`;
            NotificationEventEmitter.emit('error-event', msg);
        }
        setDialogOpen(true);
    };
    const handleClose = () => {
        setVersionHistoryItems([]);
        setDialogOpen(false);
    };

    const [items, setItems] = React.useState([]);
    const [filterStatus, setFilterStatus] = React.useState('');

    // Get all the attachments
    const getTgwAttachments = async (state) => {
        try {
            setFilterStatus(state);
            console.log(`Fetching the TGW attachments for status ${state}...`);
            let graphQlOptions;
            if (state) {
                const filter = {Status: {eq: state}, Version: {ne: "latest"}};
                graphQlOptions = graphqlOperation(getDashboarItemsForStatusFromTransitNetworkOrchestratorTables, {filter});
                graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
                const result = await API.graphql(graphQlOptions);
                const data = result.data.getDashboarItemsForStatusFromTransitNetworkOrchestratorTables.items;
                data.forEach(item => item.id = `${item.TgwId}_${item.VpcId}_${item.RequestTimeStamp}`);
                setItems(data);
            }
            else {
                graphQlOptions = graphqlOperation(getDashboarItemsFromTransitNetworkOrchestratorTables);
                graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
                const result = await API.graphql(graphQlOptions);
                const data = result.data.getDashboarItemsFromTransitNetworkOrchestratorTables.items;
                data.forEach(item => item.id = `${item.TgwId}_${item.VpcId}_${item.RequestTimeStamp}`);
                setItems(data);
            }
            console.log(`Finished fetching the TGW attachments`);
        }
        catch (error) {
            console.error(JSON.stringify(error));
            const msg = `<b>Error:</b> ${error.errors[0].errorType} <br> <b>Message:</b> ${error.errors[0].message}`;
            NotificationEventEmitter.emit('error-event', msg);
        }
    };


    const refreshTgwAttachments = async () => {
        await getTgwAttachments(filterStatus);
    };

    React.useEffect(() => {
        getTgwAttachments().then();
    },[]);

    // render the table
    return (
        <React.Fragment>
            <Title>Attachments</Title>
            <Grid container>
                <Box pt={1} pb={1}>
                    <ButtonGroup variant="contained" color="primary" aria-label="contained primary button group">
                        <Button onClick={() => {getTgwAttachments()}} color={!filterStatus ? "secondary": "primary"}>All</Button>
                        <Button onClick={() => {getTgwAttachments('approved')}} color={filterStatus === 'approved' ? "secondary": "primary"}>Approved</Button>
                        <Button onClick={() => {getTgwAttachments('auto-approved')}} color={filterStatus === 'auto-approved' ? "secondary": "primary"}>Auto Approved</Button>
                        <Button onClick={() => {getTgwAttachments('rejected')}} color={filterStatus === 'rejected' ? "secondary": "primary"}>Rejected</Button>
                        <Button onClick={() => {getTgwAttachments('auto-rejected')}} color={filterStatus === 'auto-rejected' ? "secondary": "primary"}>Auto Rejected</Button>
                        <Button onClick={() => {getTgwAttachments('failed')}} color={filterStatus === 'failed' ? "secondary": "primary"}>Failed</Button>
                    </ButtonGroup>
                    <Tooltip title="Refresh">
                        <IconButton onClick={refreshTgwAttachments}>
                            <RefreshIcon fontSize="inherit"/>
                        </IconButton>
                    </Tooltip>
                </Box>
            </Grid>
            {TransitGatewayTable(items, 'attachments', handleClickOpen)}
            <div className={classes.seeMore}>
                <Link href="#" onClick={preventDefault} color="textPrimary">
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
                <Box m={2}><Title>Viewing version history</Title></Box>
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
