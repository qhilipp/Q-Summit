import { createContext, useContext, useState } from 'react';

// Define initial state
const initialUserData = {
  gpa: null,
  languages: [],
  budget: null,
  "start-month": null,
  "start-year": null,
  "end-month": null,
  "end-year": null
};

// Create context
const UserDataContext = createContext();

// Create provider component
export function UserDataProvider({ children }) {
  const [userData, setUserData] = useState(initialUserData);
  const [apiUrl, setApiUrl] = useState('');

  // Function to update user data
  const updateUserData = (newData) => {
    setUserData(prevData => ({
      ...prevData,
      ...newData
    }));
  };

  // Function to set the API URL
  const setSubmissionUrl = (url) => {
    setApiUrl(url);
  };

  // Function to send data to API
  const sendDataToApi = async (customUrl = null) => {
    try {
      const urlToUse = customUrl || apiUrl;
      
      if (!urlToUse) {
        throw new Error('No API URL provided');
      }
      
      console.log('Sending data to API:', userData);
      console.log(JSON.stringify(userData));
      
      const response = await fetch(urlToUse, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });

      if (!response.ok) {
        throw new Error(`API call failed with status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error sending data to API:', error);
      throw error;
    }
  };

  return (
    <UserDataContext.Provider value={{ 
      userData, 
      updateUserData, 
      sendDataToApi,
      setSubmissionUrl 
    }}>
      {children}
    </UserDataContext.Provider>
  );
}

// Custom hook for using the context
export function useUserData() {
  const context = useContext(UserDataContext);
  if (!context) {
    throw new Error('useUserData must be used within a UserDataProvider');
  }
  return context;
} 