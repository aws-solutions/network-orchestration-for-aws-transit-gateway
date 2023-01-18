import React from 'react';

import Box from '@material-ui/core/Box';
import Chip from '@material-ui/core/Chip';
import ProcessingIcon from '@material-ui/icons/HourglassFull';
import AssignmentLateIcon from '@material-ui/icons/AssignmentLate';
import ErrorIcon from '@material-ui/icons/Error';
import WarningIcon from '@material-ui/icons/Warning';
import CheckCircleIcon from '@material-ui/icons/CheckCircle';


export default function StatusTableCell(row) {
    return (
        <Box>
            {(() => {
                if (row.Status === 'rejected')
                    return (<Chip variant="outlined" style={{borderColor: "red"}} icon={<WarningIcon style={{fill: "red"}}/>} label="Rejected" />)
                else if (row.Status === 'auto-approved')
                    return (<Chip variant="outlined" style={{borderColor: "green"}} icon={<CheckCircleIcon style={{fill: "green"}}/>} label="Auto Approved" />)
                else if (row.Status === 'failed')
                    return (<Chip variant="outlined" style={{borderColor: "red"}} icon={<ErrorIcon style={{fill: "red"}}/>} label="Failed" />)
                else if (row.Status === 'auto-rejected')
                    return (<Chip variant="outlined" style={{borderColor: "red"}} icon={<WarningIcon style={{fill: "red"}}/>} label="Auto Rejected" />)
                else if (row.Status === 'processing')
                    return (<Chip variant="outlined" style={{borderColor: "#ff5722"}} icon={<ProcessingIcon style={{fill: "#ff5722"}}/>} label="Processing" />)
                else if (row.Status === 'requested')
                    return (<Chip variant="outlined" style={{borderColor: "orange"}} icon={<AssignmentLateIcon style={{fill: "orange"}}/>} label="Requested" />)
                else
                    return (<Chip variant="outlined" style={{borderColor: "grey"}} icon={<AssignmentLateIcon style={{fill: "grey"}}/>} label={row.Status} />)
            })()}
        </Box>
    );
}
