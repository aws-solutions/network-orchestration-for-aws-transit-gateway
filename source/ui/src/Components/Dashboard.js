import React from 'react';
import {Route, Switch, Link} from "react-router-dom";
import {Auth} from "aws-amplify";
import clsx from 'clsx';

import { createMuiTheme, ThemeProvider } from '@material-ui/core/styles';
import { makeStyles } from '@material-ui/core/styles';
import greenColor from '@material-ui/core/colors/green';
import CssBaseline from '@material-ui/core/CssBaseline';
import Drawer from '@material-ui/core/Drawer';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import List from '@material-ui/core/List';
import Typography from '@material-ui/core/Typography';
import Divider from '@material-ui/core/Divider';
import IconButton from '@material-ui/core/IconButton';
import Container from '@material-ui/core/Container';
import Grid from '@material-ui/core/Grid';
import Paper from '@material-ui/core/Paper';
import MenuIcon from '@material-ui/icons/Menu';
import ListItem from "@material-ui/core/ListItem";
import ListItemText from "@material-ui/core/ListItemText";
import ChevronLeftIcon from '@material-ui/icons/ChevronLeft';
import ListItemIcon from "@material-ui/core/ListItemIcon";
import DashboardIcon from "@material-ui/icons/Dashboard";
import AssignmentIcon from "@material-ui/icons/Assignment";
import ExitToAppIcon from "@material-ui/icons/ExitToApp";
import Tooltip from '@material-ui/core/Tooltip';
import GithubIcon from '@material-ui/icons/GitHub';
import VpnConnectionIcon from 'react-aws-icons/dist/aws/compute/VPNConnection';
import VpcIcon from 'react-aws-icons/dist/aws/logo/VPC';
import CloudIcon from 'react-aws-icons/dist/aws/compute/AWSCloud';
import MoreHorizIcon from '@material-ui/icons/MoreHoriz';
import MenuBookIcon from '@material-ui/icons/MenuBook';
import LightThemeIcon from '@material-ui/icons/Brightness7';
import DarkThemeIcon from '@material-ui/icons/Brightness6';

import TransitGwAttachments from './TransitGwAttachments';
import TransitGwActions from './TransitGwActions';
import {NotificationTray} from './NotificationsTray';

const drawerWidth = 240;

const themeOptions = {
    palette: {
        type: 'light',
        primary: {
            light: '#3f546f',
            main: '#232f3e',
            dark: '#1a232e',
            contrastText: '#fff'
        },
        secondary: {
            main: '#f90',
            contrastText: '#fff'
        },
    },
};

const useStyles = makeStyles((theme) => ({
    root: {
        display: 'flex',
        flexGrow: 1,
    },
    toolbar: {
        paddingRight: 24, // keep right padding when drawer closed
    },
    toolbarIcon: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        padding: '0 8px',
        ...theme.mixins.toolbar,
    },
    appBar: {
        zIndex: theme.zIndex.drawer + 1,
        transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
        }),
    },
    appBarShift: {
        marginLeft: drawerWidth,
        width: `calc(100% - ${drawerWidth}px)`,
        transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
        }),
    },
    menuButton: {
        marginRight: 36,
    },
    menuButtonHidden: {
        display: 'none',
    },
    title: {
        flexGrow: 1,
    },
    drawerPaper: {
        position: 'relative',
        whiteSpace: 'nowrap',
        width: drawerWidth,
        transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
        }),
    },
    drawerPaperClose: {
        overflowX: 'hidden',
        transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
        }),
        width: theme.spacing(7),
        [theme.breakpoints.up('sm')]: {
            width: theme.spacing(9),
        },
    },
    appBarSpacer: theme.mixins.toolbar,
    content: {
        flexGrow: 1,
        height: '100vh',
        overflow: 'auto',
    },
    container: {
        flexGrow: 1,
        paddingTop: theme.spacing(4),
        paddingBottom: theme.spacing(4),
    },
    paper: {
        padding: theme.spacing(2),
        display: 'flex',
        overflow: 'auto',
        flexDirection: 'column',
    },
    fixedHeight: {
        height: 240,
    },
}));

export default function Dashboard() {
    const classes = useStyles();

    const lightTheme = createMuiTheme(themeOptions);
    const darkThemeOptions = JSON.parse(JSON.stringify(themeOptions));
    darkThemeOptions.palette.type = 'dark';
    const darkTheme = createMuiTheme(darkThemeOptions);
    const [darkMode, setDarkMode] = React.useState(false);
    const toggleTheme = () => {
        setDarkMode(!darkMode);
    };

    const signOut = () => {
        console.log('Signing out...');
        Auth.signOut()
            .then(data => window.location.reload())
            .catch(err => console.log(err));
    };

    const [open, setOpen] = React.useState(false);
    const handleDrawerOpen = () => {
        setOpen(true);
    };
    const handleDrawerClose = () => {
        setOpen(false);
    };

    return (
        <div className={classes.root}>
            <ThemeProvider theme={darkMode ? darkTheme : lightTheme}>
                <CssBaseline />
                <AppBar position="absolute" className={clsx(classes.appBar, open && classes.appBarShift)}>
                    <Toolbar className={classes.toolbar}>
                        <IconButton
                            edge="start"
                            color="inherit"
                            aria-label="open drawer"
                            onClick={handleDrawerOpen}
                            className={clsx(classes.menuButton, open && classes.menuButtonHidden)}
                        >
                            <MenuIcon />
                        </IconButton>
                        <CloudIcon size={66}/>
                        <Typography component="h1" variant="h5" color="inherit" noWrap className={classes.title}>
                            Transit Network Management Console
                        </Typography>
                        <Tooltip title="Documentation">
                            <IconButton color="inherit" onClick={() => window.open("https://docs.aws.amazon.com/solutions/latest/serverless-transit-network-orchestrator/welcome.html", "_blank")}>
                                <MenuBookIcon fontSize="inherit"/>
                            </IconButton>
                        </Tooltip>
                        <Tooltip title="Github Repo">
                            <IconButton color="inherit" onClick={() => window.open("https://github.com/awslabs/serverless-transit-network-orchestrator", "_blank")}>
                                <GithubIcon fontSize="inherit"/>
                            </IconButton>
                        </Tooltip>
                        <Tooltip title="Light/Dark mode">
                            <IconButton color="inherit" onClick={toggleTheme}>
                                {(() => {
                                    if (darkMode)
                                        return (<DarkThemeIcon fontSize="inherit"/>)
                                    else
                                        return (<LightThemeIcon fontSize="inherit"/>)
                                })()}
                            </IconButton>
                        </Tooltip>
                    </Toolbar>
                </AppBar>
                <Drawer
                    variant="permanent"
                    classes={{
                        paper: clsx(classes.drawerPaper, !open && classes.drawerPaperClose),
                    }}
                    open={open}
                >
                    <div className={classes.toolbarIcon}>
                        <VpcIcon size={48} />
                        <MoreHorizIcon style={{color: greenColor[500]}} />
                        <VpnConnectionIcon size={52} />
                        <MoreHorizIcon style={{color: greenColor[500]}} />
                        <VpcIcon size={48} />
                        <IconButton onClick={handleDrawerClose}>
                            <ChevronLeftIcon />
                        </IconButton>
                    </div>
                    <Divider />
                    <List>
                        <div>
                            <Tooltip title="Dashboard" placement="right">
                                <ListItem button component={Link} to="/">
                                    <ListItemIcon>
                                        <DashboardIcon/>
                                    </ListItemIcon>
                                    <ListItemText primary="Dashboard" />
                                </ListItem>
                            </Tooltip>
                            <Tooltip title="Actions" placement="right">
                                <ListItem button component={Link} to="/actions">
                                    <ListItemIcon>
                                        <AssignmentIcon/>
                                    </ListItemIcon>
                                    <ListItemText primary="Actions" />
                                </ListItem>
                            </Tooltip>
                            <Tooltip title="Logout" placement="right">
                                <ListItem button onClick={signOut}>
                                    <ListItemIcon>
                                        <ExitToAppIcon/>
                                    </ListItemIcon>
                                    <ListItemText primary="Logout"/>
                                </ListItem>
                            </Tooltip>
                        </div>
                    </List>
                    <Divider />
                </Drawer>
                <main className={classes.content}>
                    <div className={classes.appBarSpacer} />
                    <Container maxWidth="xl" className={classes.container}>
                        <Grid container spacing={3}>
                            <Grid item xs={12}>
                                <Paper className={classes.paper}>
                                    <Switch>
                                        <Route name="Dashboard" path="/" exact component={TransitGwAttachments}/>
                                        <Route name="Action" path="/actions" component={TransitGwActions}/>
                                    </Switch>
                                </Paper>
                            </Grid>
                        </Grid>
                    </Container>
                </main>
                <NotificationTray/>
            </ThemeProvider>
        </div>
    );
}
