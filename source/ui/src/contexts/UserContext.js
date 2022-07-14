import {createContext, useEffect, useState} from 'react';
import {Auth} from '@aws-amplify/auth';
import Amplify, {Hub} from '@aws-amplify/core';

// stno_config object is assembled by custom_resource_helper into stno_config.js and loaded by index.html.
// contains aws_appsync and cognito auth configuration.
Amplify.configure(window.stno_config);

export const UserContext = createContext();
export const UserContextProvider = (props) => {
  const [user, setUser] = useState(null);
  const [progressCircle, setProgressCircle] = useState(true);

  Hub.listen('auth', (data) => {
    switch (data.payload.event) {
      case 'signOut':
        setUser(null);
        break;
      case 'cognitoHostedUI':
        break;
      default:
        break;
    }
  })

  useEffect(() => {
    Hub.listen('auth', ({payload: {event, data}}) => {
      switch (event) {
        case 'cognitoHostedUI':
          checkUser();
          break
        case 'signOut':
          setUser(null);
          break
      }
    })
    checkUser();
  }, []);

  const checkUser = async () => {
    try {
      const responseUser = await Auth.currentAuthenticatedUser()
      setUser(responseUser)
      setProgressCircle(false)
    } catch (error) {
      setUser(null)
      setProgressCircle(false)
    }
  };

  return (
    <>
      {progressCircle ? (
        'Loading'
      ) : (
        <UserContext.Provider value={{user, setUser}}>
          {props.children}
        </UserContext.Provider>
      )}
    </>
  )
}