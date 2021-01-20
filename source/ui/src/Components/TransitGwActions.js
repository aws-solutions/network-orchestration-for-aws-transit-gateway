import React from 'react';

import {makeStyles} from '@material-ui/core/styles';
import Box from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import Slide from '@material-ui/core/Slide';
import KeyboardArrowLeftIcon from '@material-ui/icons/KeyboardArrowLeft';
import KeyboardArrowRightIcon from '@material-ui/icons/KeyboardArrowRight';
import IconButton from '@material-ui/core/IconButton';
import Grid from '@material-ui/core/Grid';
import TextField from '@material-ui/core/TextField';

import {API, Auth, graphqlOperation} from 'aws-amplify';
import {
    getActionItemsFromTransitNetworkOrchestratorTables,
    getVersionHistoryForSubnetFromTransitNetworkOrchestratorTables
} from '../graphql/queries';
import {updateTransitNetworkOrchestratorTable} from '../graphql/mutations';
import TransitGatewayTable from './TransitGatewayTable';
import TgwRequestInfo from './TgwRequestInfo';
import Title from './Title';
import HistoryTable from "./HistoryTable";
import {emitErrorEvent} from './NotificationsTray';


const useStyles = makeStyles((theme) => ({
    seeMore: {
        marginTop: theme.spacing(3),
    },
    paper: {
        padding: theme.spacing(2),
        textAlign: 'center',
        color: theme.palette.text.secondary,
    },
}));

const Transition = React.forwardRef(function Transition(props, ref) {
    return <Slide direction="up" ref={ref} {...props} />;
});

export default function TransitGatewayEntries() {
    const classes = useStyles();

    const [dialogOpen, setDialogOpen] = React.useState(false);
    const [tgwAction, setTgwAction] = React.useState('');
    const [versionHistoryItems, setVersionHistoryItems] = React.useState(false);
    const [selectedItem, setSelectedItem] = React.useState({});
    const [nextToken, setNextToken] = React.useState();
    const [nextNextToken, setNextNextToken] = React.useState();
    const [previousTokens, setPreviousTokens] = React.useState([]);
    let [items, setItems] = React.useState([]);
    const [filterText, setFilterText] = React.useState('');
    const [filteredItems, setFilteredItems] = React.useState([]);

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
    const getTgwActions = async (fetchAction) => {
        try {
            setItems([]);
            console.log(`Fetching the TGW actions...`);
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

            const graphQlOptions = graphqlOperation(getActionItemsFromTransitNetworkOrchestratorTables, params);
            graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
            const result = await API.graphql(graphQlOptions);
            let resultData = result.data.getActionItemsFromTransitNetworkOrchestratorTables;
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
    React.useEffect(() => {
        getTgwActions().then();
    },[]); // eslint-disable-line react-hooks/exhaustive-deps

    // handles opening of history or action confirmation dialog
    const openHistoryOrConfirmationDialog = async (row, action) => {
        console.log(`Action: ${action}`);
        if (action === 'history') {
            try {
                console.log(`Fetching history for selected action...`);
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
        }
        setSelectedItem(row);
        setTgwAction(action);
        setDialogOpen(true);
    };

    //Run GraphQL to accept or reject request
    const processActionRequest = async (adminAction) => {
        try {
            //get current timestamp
            const currentTimeStamp = new Date();
            const UTCTimeStamp = currentTimeStamp.toISOString();
            const currentUser = await Auth.currentUserInfo();
            console.log(`Current user = ${JSON.stringify(currentUser)}`);
            const input = {
                SubnetId: selectedItem.SubnetId,
                Version: "latest",
                Status: "processing",
                UserId: currentUser.username,
                GraphQLTimeStamp: UTCTimeStamp,
                AdminAction: adminAction
            };
            console.log(`Sending graphql mutation to update the request status: ${JSON.stringify(input)}`);
            let graphQlOptions = graphqlOperation(updateTransitNetworkOrchestratorTable, {input});
            graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
            await API.graphql(graphQlOptions);
            await getTgwActions();
        }
        catch (error) {
            emitErrorEvent(error, `Error processing TGW attachment request Subnet id = ${selectedItem.SubnetId}.`);
        }
    }

    // handles closing of the dialog based on user selected action
    const closeHistoryOrConfirmationDialog = async (confirmation) => {
        if (confirmation === true) {
            console.log(`${tgwAction}ing the tgw request...`);
            await processActionRequest(tgwAction).then(result => console.log(`Request updated successfully.`));
        }
        console.log(`Resetting the state.`);
        setDialogOpen(false);
        setVersionHistoryItems([]);
        setSelectedItem({});
    };

    // render the table
    return (
        <React.Fragment>
            <Title>Pending actions</Title>
            <Grid item xs={12} style={{textAlign: "center"}}>
                <TextField id="filled-basic" label="Federated Local Search" variant="filled" size="medium" style={{width: "40%"}}
                           value={filterText}
                           onKeyDown={processKeyPress}
                           onChange={(event) => {setFilterText(event.target.value)}}/>
            </Grid>
            {TransitGatewayTable(filteredItems, 'actions', openHistoryOrConfirmationDialog)}
            <Grid item xs={12} style={{textAlign: "center"}}>
                <IconButton color="inherit" disabled={previousTokens.length === 0} p={2} onClick={() => {getTgwActions('PREVIOUS').then()}}>
                    <KeyboardArrowLeftIcon fontSize="large"/>
                </IconButton>
                <IconButton color="inherit" disabled={!nextNextToken} p={2} onClick={() => {getTgwActions('NEXT').then()}}>
                    <KeyboardArrowRightIcon fontSize="large"/>
                </IconButton>
            </Grid>

            <Dialog
                open={dialogOpen}
                TransitionComponent={Transition}
                keepMounted
                onClose={closeHistoryOrConfirmationDialog}
                fullWidth={true}
                maxWidth = {tgwAction === 'history' ? 'xl' : 'md'}
                aria-labelledby="alert-dialog-slide-title"
                aria-describedby="alert-dialog-slide-description">
                <Box m={2}><Title>{tgwAction === 'history' ? "Viewing version history" : "Confirmation"}</Title></Box>
                <DialogContent>
                    {(() => {
                        if (tgwAction === 'history') {
                            return (
                                HistoryTable(versionHistoryItems)
                            );
                        }
                        else if (tgwAction === 'accept') {
                            return (
                                <Box>
                                    <DialogContentText>
                                        Are you sure you want to <b>ACCEPT</b> this request?
                                    </DialogContentText>
                                    {TgwRequestInfo(selectedItem, classes)}
                                </Box>
                            );
                        }
                        else if (tgwAction === 'reject') {
                            return (
                                <Box>
                                    <DialogContentText>
                                        Are you sure you want to <b>REJECT</b> this request?
                                    </DialogContentText>
                                    {TgwRequestInfo(selectedItem, classes)}
                                </Box>
                            );
                        }
                    })()}
                </DialogContent>
                <DialogActions>
                    {(() => {
                        if (tgwAction === 'history') {
                            return (
                                <Button variant="contained" onClick={closeHistoryOrConfirmationDialog} color="primary">Close</Button>
                            );
                        }
                        else
                            return(
                                <Box display="flex" flexDirection="row">
                                    <Box p={1}>
                                        <Button variant="contained" onClick={() => {closeHistoryOrConfirmationDialog(true).then()}} color="secondary">Yes</Button>
                                    </Box>
                                    <Box p={1}>
                                        <Button variant="contained" onClick={() => {closeHistoryOrConfirmationDialog(false).then()}} color="primary">No</Button>
                                    </Box>
                                </Box>
                            );
                    })()}
                </DialogActions>
            </Dialog>

        </React.Fragment>
    );
}
