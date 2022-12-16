import { createContext, useEffect, useState } from "react";
import { Auth } from "@aws-amplify/auth";
import Amplify, { Hub } from "@aws-amplify/core";

// stno_config object is assembled by custom_resource_helper into stno_config.js and loaded by index.html.
// contains aws_appsync and cognito auth configuration.
Amplify.configure(window.stno_config);

export const UserContext = createContext();
export const UserContextProvider = (props) => {
  const [user, setUser] = useState(null);
  const [busy, setBusy] = useState(true);

  Hub.listen("auth", (data) => {
    if (data.payload.event === "signOut") {
      setUser(null);
    }
  });

  useEffect(() => {
    Hub.listen("auth", ({ payload: { event, data } }) => {
      if (event === "cognitoHostedUI") {
        checkUser();
      } else if (event === "signOut") {
        setUser(null);
      }
    });
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const responseUser = await Auth.currentAuthenticatedUser();
      setUser(responseUser);
      setBusy(false);
    } catch (error) {
      setUser(null);
      setBusy(false);
    }
  };

  if (busy) {
    return <div>Loading</div>;
  } else return (
    <UserContext.Provider value={{ user, setUser }}>
      {props.children}
    </UserContext.Provider>
  );
};