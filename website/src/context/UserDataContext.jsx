import { createContext, useContext, useState } from 'react';

// Define initial state
const initialUserData = {
  university: null,
  major: null,
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
    return new Promise(resolve => {
      setUserData(prevData => {
        const updatedData = {
          ...prevData,
          ...newData
        };
        // Resolve with the newly updated data
        resolve(updatedData);
        return updatedData;
      });
    });
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
      
      // Debug: Log all user data that will be sent to the API
      console.log('Preparing to send data to API:', userData);
      
      // Create a copy of userData with the correct field names for the API
      const apiFormattedData = {
        university: userData.university,
        major: userData.major,
        gpa: userData.gpa,
        languages: userData.languages,
        budget: userData.budget,
        // Convert dash format to underscore format for date fields
        start_month: userData['start-month'],
        start_year: userData['start-year'],
        end_month: userData['end-month'],
        end_year: userData['end-year']
      };
      
      // Log the payload that will be sent
      console.log('API payload:', apiFormattedData);
      
      // Set up request using the format provided
      const myHeaders = new Headers();
      myHeaders.append("Content-Type", "application/json");
      
      const raw = JSON.stringify(apiFormattedData);
      
      // Log the equivalent curl command
      console.log(`curl -X POST \\
  "${urlToUse}" \\
  -H "Content-Type: application/json" \\
  -d '${raw}'`);
      
      const requestOptions = {
        method: "POST",
        headers: myHeaders,
        body: raw,
        redirect: "follow"
      };
      
      // Use Promise-based approach as requested
      return new Promise((resolve, reject) => {
        fetch(urlToUse, requestOptions)
          .then(response => {
            if (!response.ok) {
              throw new Error(`API call failed with status: ${response.status}`);
            }
            return response.json();
          })
          .then(result => {
            console.log('API response:', result);
            resolve(result);
          })
          .catch(error => {
            console.error('Error sending data to API:', error);
            reject(error);
          });
      });
    } catch (error) {
      console.error('Error in sendDataToApi setup:', error);
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