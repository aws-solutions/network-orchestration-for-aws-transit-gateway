/*********************************************************************************************************************
 *  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                           *
 *                                                                                                                    *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance        *
 *  with the License. A copy of the License is located at                                                             *
 *                                                                                                                    *
 *      http://www.apache.org/licenses/LICENSE-2.0                                                                                    *
 *                                                                                                                    *
 *  or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES *
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions    *
 *  and limitations under the License.                                                                                *
 *********************************************************************************************************************/

import React from 'react';
import { BrowserRouter as Router, Route, Link, Switch } from "react-router-dom";
import {withAuthenticator,AmplifyTheme} from 'aws-amplify-react';
import Amplify, { Auth } from 'aws-amplify';

//Icons
import { library } from '@fortawesome/fontawesome-svg-core';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faAws } from '@fortawesome/free-brands-svg-icons';
import { faBars,faCog,faPlusSquare,faArrowAltCircleRight, faSyncAlt } from '@fortawesome/free-solid-svg-icons';

//Components
import Dashboard from './Components/Dashboard/Dashboard';
import Action from './Components/Action/Action';

//css
import 'bootstrap/dist/css/bootstrap.css';

declare var stno_config;

Amplify.configure({
  Auth: {
    region: stno_config.aws_project_region,
    userPoolId: stno_config.aws_user_pools_id,
    userPoolWebClientId: stno_config.aws_user_pools_web_client_id,
    identityPoolId: stno_config.aws_cognito_identity_pool_id
  }
});

let myAppSyncConfig={
  aws_appsync_graphqlEndpoint: stno_config.aws_appsync_graphqlEndpoint,
  aws_appsync_region: stno_config.aws_appsync_region,
  aws_appsync_authenticationType: stno_config.aws_appsync_authenticationType,
  aws_content_delivery_bucket: stno_config.aws_content_delivery_bucket,
  aws_content_delivery_bucket_region: stno_config.aws_project_region,
  aws_content_delivery_url: stno_config.aws_content_delivery_url
}

Amplify.configure(myAppSyncConfig);

library.add(
  faAws,
  faBars,
  faCog,
  faPlusSquare,
  faArrowAltCircleRight,
  faSyncAlt
)

function NoMatch({ location }) {
  return (
    <div>
      <h3>
        No match for <code>{location.pathname}</code>
      </h3>
    </div>
  );
}

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
        <div>
          <nav className="topnav">
            <FontAwesomeIcon icon={faAws} size="2x" color="#FF9900" id="logo" />
            <h1 > Transit Network Managment Console</h1>
            <Link to="" onClick={this.signOut}>Sign Out</Link>
          </nav>

          <nav className ="sidenav">
            <Link to="/">
              <FontAwesomeIcon icon={faBars} /> Dashboard
            </Link>
            <Link to={{pathname:"/action/"+this.props.authData.username, state:this.props.authData.username+","+this.props.authData.signInUserSession.idToken.payload['cognito:groups'].join()}}>
               <FontAwesomeIcon icon={faBars} /> Action Items
            </Link>   
          </nav>

          <div className="main">
            <Switch>
              <Route name="Dashboard" path="/" exact component={Dashboard} />
              <Route name="Action" path="/action/" component={Action} />
              <Route component={NoMatch} />
            </Switch>
          </div>
        </div>
      </Router>
    );
  }
};

//customize authenticator theme
const theme={
    sectionFooterSecondaryContent:{
      ...AmplifyTheme.sectionFooterSecondaryContent,
      display:"none"
    },
    sectionHeader:{
      ...AmplifyTheme.sectionFooter,
      backgroundColor:"#31465f",
      color:"white"
    }
};


// export default withAuthenticator(App,{includeGreetings:true},[],null,theme);
// export default withAuthenticator(App,true,[],null,theme);
export default withAuthenticator(App,false,[],null,theme);