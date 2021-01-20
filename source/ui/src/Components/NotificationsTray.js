import React, {useEffect} from 'react';
import EventEmitter from 'events';
import MuiAlert from '@material-ui/lab/Alert';
import Snackbar from '@material-ui/core/Snackbar';

export const NotificationEventEmitter = new EventEmitter();

export const NotificationTray = () => {
    const [notificationMessage, setNotificationMessage] = React.useState(null);
    const [showNotification, setShowNotification] = React.useState(false);
    const openNotification = (message) => {
        // console.debug(`Received error event. Opening the notification tray. Message = ${message}`);
        setNotificationMessage(message);
        setShowNotification(true);
    };
    const closeNotification = () => {
        setShowNotification(false);
    };

    useEffect(() => {
        console.log(`Registering listener to notification event emitter.`);
        NotificationEventEmitter.on('error-event', openNotification);

        return () => {
            console.log("Unregistering notification emitter listener.");
            NotificationEventEmitter.removeListener('error-event', openNotification);
        }
    }, []);

    return (
        <React.Fragment>
            <Snackbar
                anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
                open={showNotification}
                onClose={closeNotification}
            >
                <MuiAlert severity="error" elevation={6} variant="filled">
                    <div dangerouslySetInnerHTML={{ __html: notificationMessage }}/>
                </MuiAlert>
            </Snackbar>
        </React.Fragment>
    );
}

export const emitErrorEvent = (error, errorMsg) => {
    console.error(error);
    if (error.errors && error.errors.length > 0) {
        const msg = `${errorMsg} <br> Error: ${error.errors[0].errorType} <br> Message: ${error.errors[0].message}`;
        NotificationEventEmitter.emit('error-event', msg);
    }
    else {
        const msg = `<b>Unknown</b> ${error}`;
        NotificationEventEmitter.emit('error-event', msg);
    }
}
