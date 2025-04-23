import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Button from '../Button/Button';
import './Welcome.css';

const Welcome = () => {
  const [displayText, setDisplayText] = useState('');
  const fullText = "Study AIbroad";
  const navigate = useNavigate();

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
        <Button onClick={() => navigate('/university')}>
          Let's go
        </Button>
      </div>
    </div>
  );
};

export default Welcome; 