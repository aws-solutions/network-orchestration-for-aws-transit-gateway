import React from 'react';

import {makeStyles} from '@material-ui/core/styles';
import Link from '@material-ui/core/Link';
import Box from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import DialogTitle from '@material-ui/core/DialogTitle';
import Slide from '@material-ui/core/Slide';

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

function preventDefault(event) {
    event.preventDefault();
}

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

    let [items, setItems] = React.useState([]);
    // Get all the attachments
    const getTgwActions = async () => {
        setItems([]);
        console.log(`Fetching the TGW actions...`);
        let graphQlOptions = graphqlOperation(getActionItemsFromTransitNetworkOrchestratorTables);
        graphQlOptions.authMode = 'AMAZON_COGNITO_USER_POOLS';
        const result = await API.graphql(graphQlOptions);
        setItems(result.data.getActionItemsFromTransitNetworkOrchestratorTables.items);
        console.log(`Finished fetching the TGW attachments`);
    };
    React.useEffect(getTgwActions,[]);

    // handles opening of history or action confirmation dialog
    const handleClickOpen = async (row, action) => {
        console.log(`Action: ${action}`);
        if (action === 'history') {
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
            // await API.graphql(graphQlOptions);
            await getTgwActions();
        } catch (error) {
            console.error(error);
        }
    }

    // handles closing of the dialog based on user selected action
    const handleClose = async (confirmation) => {
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
            {TransitGatewayTable(items, 'actions', handleClickOpen)}
            <div className={classes.seeMore}>
                <Link color="primary" href="#" onClick={preventDefault}>
                    See more actions
                </Link>
            </div>

            <Dialog
                open={dialogOpen}
                TransitionComponent={Transition}
                keepMounted
                onClose={handleClose}
                fullWidth={true}
                maxWidth = {tgwAction === 'history' ? 'xl' : 'md'}
                aria-labelledby="alert-dialog-slide-title"
                aria-describedby="alert-dialog-slide-description">
                <DialogTitle id="alert-dialog-slide-title">{tgwAction === 'history' ? "Viewing version history" : "Confirmation"}</DialogTitle>
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
                                <Button variant="contained" onClick={handleClose} color="primary">Close</Button>
                            );
                        }
                        else
                            return(
                                <Box display="flex" flexDirection="row">
                                    <Box p={1}>
                                        <Button variant="contained" onClick={() => {handleClose(true)}} color="primary">Yes</Button>
                                    </Box>
                                    <Box p={1}>
                                        <Button variant="contained" onClick={() => {handleClose(false)}} color="secondary">No</Button>
                                    </Box>
                                </Box>
                            );
                    })()}
                </DialogActions>
            </Dialog>

        </React.Fragment>
    );
}
