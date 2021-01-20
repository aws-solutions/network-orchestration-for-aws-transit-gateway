import React from 'react';

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
import KeyboardArrowLeftIcon from '@material-ui/icons/KeyboardArrowLeft';
import KeyboardArrowRightIcon from '@material-ui/icons/KeyboardArrowRight';
import TextField from '@material-ui/core/TextField';

import {API, graphqlOperation} from 'aws-amplify';
import {
    getDashboarItemsForStatusFromTransitNetworkOrchestratorTables,
    getDashboarItemsFromTransitNetworkOrchestratorTables,
    getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables
} from '../graphql/queries';

import Title from './Title';
import HistoryTable from './HistoryTable';
import TransitGatewayTable from './TransitGatewayTable';
import {emitErrorEvent} from './NotificationsTray';

const Transition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

export default function TransitGatewayEntries() {

    const [dialogOpen, setDialogOpen] = React.useState(false);
    let [versionHistoryItems, setVersionHistoryItems] = React.useState(false);
    const openAttachmentHistoryDialog = async (row) => {
        try {
            console.log(`Fetching history for selected attachment...`);
            const filter = {SubnetId: {eq: row.SubnetId}, Version: {ne: "latest"}};
            let graphQlOptions = graphqlOperation(getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables, {filter});
            graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
            const result = await API.graphql(graphQlOptions);
            const data = result.data.getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables.items;
            data.forEach(item => item.id = `${item.TgwId}_${item.VpcId}_${item.RequestTimeStamp}`);
            setVersionHistoryItems(data);
        }
        catch (error) {
            emitErrorEvent(error, `Error getting version history for subnet ID ${row.SubnetId}.`);
        }
        setDialogOpen(true);
    };
    const closeAttachmentHistoryDialog = () => {
        setVersionHistoryItems([]);
        setDialogOpen(false);
    };

    const [items, setItems] = React.useState([]);
    const [filterStatus, setFilterStatus] = React.useState('');
    const [filterText, setFilterText] = React.useState('');
    const [filteredItems, setFilteredItems] = React.useState([]);
    const [nextToken, setNextToken] = React.useState();
    const [nextNextToken, setNextNextToken] = React.useState();
    const [previousTokens, setPreviousTokens] = React.useState([]);

    const filterData = (data) => {
        if (filterText) {
            console.log(`Filtering by ${filterText}...`);
            let filtered = [];
            data.forEach(item => {
                for (const prop in item) {
                    if (prop && item[prop] && item[prop].toString().includes(filterText)) {
                        filtered.push(item);
                        break;
                    }
                }
            });
            setFilteredItems(filtered);
        }
        else {
            console.log(`No Filtering.. Show all data.`);
            setFilteredItems(data);
        }
    };

    const processKeyPress = (event) => {
        if (event.key === 'Enter') {
            filterData(items);
        }
    };

    // Get all the attachments
    const getTgwAttachments = async (state, fetchAction) => {
        try {
            setFilterStatus(state);
            console.log(`Fetching the TGW attachments for status ${state} and action ${fetchAction}...`);
            let graphQlOptions;
            let resultData;
            const params = {};
            switch (fetchAction) {
                case 'PREVIOUS':
                    const token = previousTokens.pop();
                    setNextToken(token);
                    setPreviousTokens([...previousTokens]);
                    setNextNextToken(null);
                    params.nextToken = token;
                    break;
                case 'NEXT':
                    setPreviousTokens((prev) => [...prev, nextToken]);
                    setNextToken(nextNextToken);
                    setNextNextToken(null);
                    params.nextToken = nextNextToken;
                    break;
                default:
                    console.log(`Resetting pagination tokens...`);
                    setNextToken(null);
                    setNextNextToken(null);
                    setPreviousTokens([]);
                    break;
            }

            if (state) {
                params.filter = {Status: {eq: state}, Version: {ne: "latest"}};
                graphQlOptions = graphqlOperation(getDashboarItemsForStatusFromTransitNetworkOrchestratorTables, params);
                graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
                const result = await API.graphql(graphQlOptions);
                resultData = result.data.getDashboarItemsForStatusFromTransitNetworkOrchestratorTables;
            }
            else {
                graphQlOptions = graphqlOperation(getDashboarItemsFromTransitNetworkOrchestratorTables, params);
                graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
                const result = await API.graphql(graphQlOptions);
                resultData = result.data.getDashboarItemsFromTransitNetworkOrchestratorTables;
            }

            setNextNextToken(resultData.nextToken);

            const data = resultData.items;
            data.forEach(item => item.id = `${item.TgwId}_${item.VpcId}_${item.RequestTimeStamp}`);
            setItems(data);
            filterData(data);
            console.log(`Finished fetching the TGW attachments`);
        }
        catch (error) {
            emitErrorEvent(error, '');
        }
    };

    const refreshTgwAttachments = async () => {
        await getTgwAttachments(filterStatus);
    };

    React.useEffect(() => {
        getTgwAttachments().then();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // render the table
    return (
        <React.Fragment>
            <Title>Attachments</Title>
            <Grid container>
                <Box pt={1} pb={1}>
                    <ButtonGroup variant="contained" color="primary" aria-label="contained primary button group">
                        <Button onClick={() => {getTgwAttachments().then()}} color={!filterStatus ? "secondary": "primary"}>All</Button>
                        <Button onClick={() => {getTgwAttachments('approved').then()}} color={filterStatus === 'approved' ? "secondary": "primary"}>Approved</Button>
                        <Button onClick={() => {getTgwAttachments('auto-approved').then()}} color={filterStatus === 'auto-approved' ? "secondary": "primary"}>Auto Approved</Button>
                        <Button onClick={() => {getTgwAttachments('rejected').then()}} color={filterStatus === 'rejected' ? "secondary": "primary"}>Rejected</Button>
                        <Button onClick={() => {getTgwAttachments('auto-rejected').then()}} color={filterStatus === 'auto-rejected' ? "secondary": "primary"}>Auto Rejected</Button>
                        <Button onClick={() => {getTgwAttachments('failed').then()}} color={filterStatus === 'failed' ? "secondary": "primary"}>Failed</Button>
                    </ButtonGroup>
                    <Tooltip title="Refresh">
                        <IconButton onClick={refreshTgwAttachments}>
                            <RefreshIcon fontSize="inherit"/>
                        </IconButton>
                    </Tooltip>
                </Box>
            </Grid>
            <Grid item xs={12} style={{textAlign: "center"}}>
                <TextField id="filled-basic" label="Federated Local Search" variant="filled" size="medium" style={{width: "40%"}}
                           value={filterText}
                           onKeyDown={processKeyPress}
                           onChange={(event) => {setFilterText(event.target.value)}}/>
            </Grid>
            {TransitGatewayTable(filteredItems, 'attachments', openAttachmentHistoryDialog)}
            <Grid item xs={12} style={{textAlign: "center"}}>
                <IconButton color="inherit" disabled={previousTokens.length === 0} p={2} onClick={() => {getTgwAttachments(filterStatus, 'PREVIOUS').then()}}>
                    <KeyboardArrowLeftIcon fontSize="large"/>
                </IconButton>
                <IconButton color="inherit" disabled={!nextNextToken} p={2} onClick={() => {getTgwAttachments(filterStatus, 'NEXT').then()}}>
                    <KeyboardArrowRightIcon fontSize="large"/>
                </IconButton>
            </Grid>

            <Dialog
                open={dialogOpen}
                TransitionComponent={Transition}
                keepMounted
                onClose={closeAttachmentHistoryDialog}
                fullWidth={true}
                maxWidth = {'xl'}
                aria-labelledby="alert-dialog-slide-title"
                aria-describedby="alert-dialog-slide-description">
                <Box m={2}><Title>Viewing version history</Title></Box>
                <DialogContent>
                    {HistoryTable(versionHistoryItems)}
                </DialogContent>
                <DialogActions>
                    <Button variant="contained" onClick={closeAttachmentHistoryDialog} color="primary">
                        Close
                    </Button>
                </DialogActions>
            </Dialog>
        </React.Fragment>
    );
}
