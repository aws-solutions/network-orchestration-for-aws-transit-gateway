/***********************************************************************
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 ***********************************************************************/

import React, {useContext} from "react";
import {BrowserRouter as Router, Link, Route, Switch} from "react-router-dom";
import {Logger} from "@aws-amplify/core";
import {Auth} from "@aws-amplify/auth";

//Icons
import {library} from "@fortawesome/fontawesome-svg-core";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome";
import {faAws} from "@fortawesome/free-brands-svg-icons";
import {faArrowAltCircleRight, faBars, faCog, faPlusSquare, faSyncAlt,} from "@fortawesome/free-solid-svg-icons";

import Dashboard from "./Components/Dashboard/Dashboard";
import Action from "./Components/Action/Action";

import "bootstrap/dist/css/bootstrap.css";
import {UserContext} from "./contexts/UserContext";

const LOGGER = new Logger("App", "DEBUG");

library.add(
  faAws,
  faBars,
  faCog,
  faPlusSquare,
  faArrowAltCircleRight,
  faSyncAlt
);

function NoMatch({location}) {
  return (
    <div>
      <h3>
        No match for <code>{location.pathname}</code>
      </h3>
    </div>
  );
}

const signOut = async () => {
  await Auth.signOut().catch((error) => {
    LOGGER.error("Error occurred while signing out.", error);
  });
  window.location.reload();
}

function App() {
  const {user} = useContext(UserContext);
  LOGGER.debug(`User: ${JSON.stringify(user)}`);
  const groups = user && user.signInUserSession.idToken.payload["cognito:groups"] || ["none"];
  LOGGER.debug(`User Groups: ${groups}`);

  if (!user) {
    Auth.federatedSignIn().then((response) => {
      LOGGER.debug(`Federated sign in successful: ${response}`);
    });
    return <div>Redirecting to login...</div>
  } else {
    return (
      <Router>
        <div>
          <nav className="topnav">
            <FontAwesomeIcon icon={faAws} size="2x" color="#FF9900" id="logo"/>
            <h1> Transit Network Managment Console</h1>
            <Link to="" onClick={signOut}>
              Sign Out
            </Link>
          </nav>

          <nav className="sidenav">
            <Link to="/">
              <FontAwesomeIcon icon={faBars}/> Dashboard
            </Link>
            <Link
              to={{
                pathname: "/action/" + user.username,
                state: user.username + "," + groups.join(),
              }}
            >
              <FontAwesomeIcon icon={faBars}/> Action Items
            </Link>
          </nav>

          <div className="main">
            <Switch>
              <Route name="Dashboard" path="/" exact component={Dashboard}/>
              <Route name="Action" path="/action/" component={Action}/>
              <Route component={NoMatch}/>
            </Switch>
          </div>
        </div>
      </Router>
    );
  }
}


export default App;
