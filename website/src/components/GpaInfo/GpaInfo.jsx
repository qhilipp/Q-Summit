import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import Button from '../Button/Button.jsx';
import { useUserData } from '../../context/UserDataContext';
import './GpaInfo.css';

const GpaInfo = () => {
  const navigate = useNavigate();
  const [gpa, setGpa] = useState('');
  const [error, setError] = useState('');
  const { updateUserData } = useUserData();

  const handleGpaChange = (e) => {
    const value = e.target.value;
    // Allow only numbers and one decimal point
    if (value === '' || /^(\d+)?(\.\d{0,2})?$/.test(value)) {
      setGpa(value);
      
      // Clear error if valid or empty
      if (error) setError('');
    }
  };

  const handleContinue = () => {
    // Basic validation
    if (!gpa) {
      setError('Please enter your GPA');
      return;
    }
    
    const gpaNum = parseFloat(gpa);
    if (isNaN(gpaNum) || gpaNum < 0 || gpaNum > 4.0) {
      setError('Please enter a valid GPA between 0.0 and 4.0');
      return;
    }

    // Save GPA to context
    updateUserData({ gpa: gpaNum });
    
    // If valid, proceed to next page
    navigate('/languages');
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 1,
        when: "beforeChildren",
        staggerChildren: 0.1
      }
    }
  };

  const titleVariants = {
    hidden: { y: 50, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 10
      }
    }
  };

  const buttonVariants = {
    hidden: { scale: 0, opacity: 0 },
    visible: {
      scale: 1,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 200,
        damping: 15,
        delay: 0.5
      }
    },
    hover: {
      scale: 1.05,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 10
      }
    }
  };

  return (
    <motion.div
      className="gpa-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="gpa-heading" variants={titleVariants}>
        What is your GPA?
      </motion.h1>

      <div className="input-container">
        <div className="input-wrapper">
          <input 
            type="text" 
            placeholder="Your GPA (e.g., 3.5)" 
            className={`info-input ${error ? 'error' : ''}`}
            value={gpa}
            onChange={handleGpaChange}
          />
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
      
      <Button onClick={handleContinue}>
        Continue
      </Button>
    </motion.div>
  );
};

export default GpaInfo; 