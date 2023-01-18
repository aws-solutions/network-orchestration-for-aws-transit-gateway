/*********************************************************************************************************************
 *  Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                    *
 *                                                                                                                    *
 *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import React from 'react';
import {BrowserRouter as Router} from "react-router-dom";
import {withAuthenticator, AmplifyTheme} from 'aws-amplify-react';
import Amplify, {Auth} from 'aws-amplify';

//css
import 'bootstrap/dist/css/bootstrap.css';

//test
import Dashboard from './Components/Dashboard';

declare
var stno_config;

Amplify.configure({
    Auth: {
        region: stno_config.aws_project_region,
        userPoolId: stno_config.aws_user_pools_id,
        userPoolWebClientId: stno_config.aws_user_pools_web_client_id,
        identityPoolId: stno_config.aws_cognito_identity_pool_id
    }
});

let myAppSyncConfig = {
    aws_appsync_graphqlEndpoint: stno_config.aws_appsync_graphqlEndpoint,
    aws_appsync_region: stno_config.aws_appsync_region,
    aws_appsync_authenticationType: stno_config.aws_appsync_authenticationType,
    aws_content_delivery_bucket: stno_config.aws_content_delivery_bucket,
    aws_content_delivery_bucket_region: stno_config.aws_project_region,
    aws_content_delivery_url: stno_config.aws_content_delivery_url
}

Amplify.configure(myAppSyncConfig);

class App extends React.Component {

    constructor(props) {
        super(props);
        this.signOut = this.signOut.bind(this);
    };

    signOut() {
        //window.location.reload();
        Auth.signOut()
            .then(data => console.log(data))
            .catch(err => console.log(err));
    };

    render() {
        return (
            <Router>
                <Dashboard />
            </Router>
        );
    }
}

//customize authenticator theme
const theme = {
    formContainer: {
        margin: '0px',
    },
    formSection: {
        margin: '5% auto 0',
    },
    sectionFooterSecondaryContent: {
        ...AmplifyTheme.sectionFooterSecondaryContent,
        display: "none"
    },
    oAuthSignInButton: {
        backgroundColor: '#1a232e',
        color: '#fff',
    },
    button: {
        backgroundColor: "#1a232e"
    },
    a: {
        color: "#1a232e"
    }
};


export default withAuthenticator(App, false, [], null, theme);
