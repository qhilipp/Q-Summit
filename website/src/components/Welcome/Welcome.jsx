import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Button from '../Button/Button';
import './Welcome.css';

const Welcome = () => {
  const [displayText, setDisplayText] = useState('');
  const fullText = "Study AIbroad";
  const navigate = useNavigate();

  const handleBackendCall = async () => {
    try {
      const response = await fetch('http://q-hacks-backend.westeurope.azurecontainer.io/items/5?q=somequery', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      console.log('Backend response:', data);
    } catch (error) {
      console.error('Error calling backend:', error);
    }
  };

  useEffect(() => {
    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex <= fullText.length) {
        setDisplayText(fullText.slice(0, currentIndex));
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, 100);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="welcome-container">
      <div className="welcome-content">
        <motion.h1 
          className="welcome-heading"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          {displayText}
        </motion.h1>
        <div className="button-container">
          <Button onClick={() => navigate('/university')}>
            Let's go
          </Button>
          <Button onClick={handleBackendCall} style={{ marginTop: '10px' }}>
            Call Backend
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Welcome; 